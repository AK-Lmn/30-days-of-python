from datetime import datetime
import os
from pathlib import Path
import shutil
from typing import Optional
from organizer.duplicates import compute_file_hash
from organizer.history import HistoryManager
from organizer.models import (
    ConflictResolution,
    FileItem,
    OrganizeAction,
    OrganizeMode,
    OrganizeResult,
    OrganizeStrategy,
    OrganizerConfig,
    UndoResult,
)
from organizer.rules import (
    is_ignored_dir,
    is_ignored_file,
    resolve_relative_destination,
)


def get_file_item(path: Path) -> Optional[FileItem]:
    try:
        stat_info = path.stat()
        return FileItem(
            path=path,
            name=path.name,
            extension=path.suffix,
            size=stat_info.st_size,
            modified_at=datetime.fromtimestamp(stat_info.st_mtime),
            created_at=datetime.fromtimestamp(stat_info.st_ctime),
        )
    except OSError:
        return None


def scan_directory(
    directory: Path,
    recursive: bool = False,
    include_hidden: bool = False,
    config: Optional[OrganizerConfig] = None,
    exclude_dirs: Optional[set[str]] = None,
) -> list[FileItem]:
    if not directory.is_dir():
        return []

    raw_patterns = config.ignored_patterns if config else [".*"]
    if include_hidden:
        ignored_patterns = [p for p in raw_patterns if not p.startswith(".")]
    else:
        ignored_patterns = list(raw_patterns)

    ignored_dirs = config.ignored_directories if config else [".git", ".venv"]
    excluded = set(exclude_dirs or set())
    for d in ignored_dirs:
        excluded.add(d.lower())

    results: list[FileItem] = []

    if recursive:
        for root, dirs, files in os.walk(directory):
            dirs[:] = [
                d for d in dirs
                if (include_hidden or not d.startswith("."))
                and not is_ignored_dir(d, list(excluded))
            ]
            for file_name in files:
                if not include_hidden and file_name.startswith("."):
                    continue
                if is_ignored_file(file_name, ignored_patterns):
                    continue
                file_path = Path(root) / file_name
                if file_path.is_file() and not file_path.is_symlink():
                    item = get_file_item(file_path)
                    if item:
                        results.append(item)
    else:
        for entry in directory.iterdir():
            if not entry.is_file() or entry.is_symlink():
                continue
            if not include_hidden and entry.name.startswith("."):
                continue
            if is_ignored_file(entry.name, ignored_patterns):
                continue
            item = get_file_item(entry)
            if item:
                results.append(item)

    return results


def resolve_collision(
    target_path: Path,
    source_path: Path,
    conflict_resolution: ConflictResolution,
) -> tuple[Optional[Path], Optional[str]]:
    if not target_path.exists():
        return target_path, None

    if target_path.resolve() == source_path.resolve():
        return None, "File is already at destination"

    if conflict_resolution == ConflictResolution.SKIP:
        return None, "Destination file already exists (skipped)"

    if conflict_resolution == ConflictResolution.OVERWRITE:
        return target_path, "Overwriting existing file"

    if conflict_resolution == ConflictResolution.HASH_CHECK:
        source_hash = compute_file_hash(source_path)
        dest_hash = compute_file_hash(target_path)
        if source_hash == dest_hash:
            return None, "Identical file already exists at destination (skipped)"

    stem = target_path.stem
    suffix = target_path.suffix
    parent = target_path.parent
    counter = 1

    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate, "Renamed to avoid collision with existing file"
        counter += 1


def plan_organization(
    source_dir: Path,
    strategy: OrganizeStrategy,
    config: OrganizerConfig,
    mode: OrganizeMode = OrganizeMode.MOVE,
    recursive: bool = False,
    include_hidden: bool = False,
    date_subfolders: bool = False,
    conflict_resolution: ConflictResolution = ConflictResolution.RENAME,
    destination_dir: Optional[Path] = None,
) -> list[OrganizeAction]:
    base_dest = (destination_dir or source_dir).resolve()
    target_category_dirs = set(config.categories.keys())
    if strategy == OrganizeStrategy.CATEGORY:
        target_category_dirs.add("Other")
        target_category_dirs.add("Custom")

    files = scan_directory(
        directory=source_dir,
        recursive=recursive,
        include_hidden=include_hidden,
        config=config,
        exclude_dirs=target_category_dirs if base_dest == source_dir.resolve() else None,
    )

    actions: list[OrganizeAction] = []
    for item in files:
        category, rel_dest = resolve_relative_destination(
            item=item,
            strategy=strategy,
            config=config,
            date_subfolders=date_subfolders,
        )
        proposed_dest = base_dest / rel_dest
        final_dest, reason = resolve_collision(
            target_path=proposed_dest,
            source_path=item.path,
            conflict_resolution=conflict_resolution,
        )

        if final_dest is None:
            actions.append(
                OrganizeAction(
                    source_path=item.path,
                    destination_path=proposed_dest,
                    category=category,
                    action_type="skip",
                    size=item.size,
                    reason=reason,
                )
            )
        else:
            act_type = "move" if mode == OrganizeMode.MOVE else "copy"
            actions.append(
                OrganizeAction(
                    source_path=item.path,
                    destination_path=final_dest,
                    category=category,
                    action_type=act_type,
                    size=item.size,
                    reason=reason,
                )
            )

    return actions


def execute_organization(
    actions: list[OrganizeAction],
    mode: OrganizeMode,
    dry_run: bool,
    source_dir: Path,
    strategy: str,
    history_manager: Optional[HistoryManager] = None,
) -> OrganizeResult:
    result = OrganizeResult(
        session_id=None,
        total_files_scanned=len(actions),
    )

    if dry_run:
        for act in actions:
            result.actions.append(act)
            if act.action_type == "skip":
                result.skipped_count += 1
            elif act.action_type == "move":
                result.moved_count += 1
                result.bytes_processed += act.size
            elif act.action_type == "copy":
                result.copied_count += 1
                result.bytes_processed += act.size
        return result

    executed_actions: list[OrganizeAction] = []
    for act in actions:
        if act.action_type == "skip":
            result.actions.append(act)
            result.skipped_count += 1
            continue

        try:
            act.destination_path.parent.mkdir(parents=True, exist_ok=True)
            if act.action_type == "move":
                shutil.move(str(act.source_path), str(act.destination_path))
                result.moved_count += 1
            else:
                shutil.copy2(str(act.source_path), str(act.destination_path))
                result.copied_count += 1

            result.bytes_processed += act.size
            executed_actions.append(act)
            result.actions.append(act)
        except OSError as e:
            failed_act = OrganizeAction(
                source_path=act.source_path,
                destination_path=act.destination_path,
                category=act.category,
                action_type="skip",
                size=act.size,
                reason=f"Error: {e}",
            )
            result.actions.append(failed_act)
            result.skipped_count += 1

    if history_manager and executed_actions:
        session_id = history_manager.record_session(
            source_dir=source_dir,
            strategy=strategy,
            actions=executed_actions,
        )
        result.session_id = session_id

    return result


def execute_undo(
    history_manager: HistoryManager,
    session_id: Optional[int] = None,
) -> Optional[UndoResult]:
    if session_id is not None:
        session_data = history_manager.get_session_by_id(session_id)
    else:
        session_data = history_manager.get_last_active_session()

    if not session_data:
        return None

    actual_id, actions = session_data
    restored = 0
    failed = 0
    cleaned_dirs: list[Path] = []
    candidate_empty_dirs: set[Path] = set()

    for act in actions:
        if act.action_type == "move":
            if act.destination_path.exists():
                try:
                    act.source_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(act.destination_path), str(act.source_path))
                    restored += 1
                    candidate_empty_dirs.add(act.destination_path.parent)
                except OSError:
                    failed += 1
            else:
                failed += 1
        elif act.action_type == "copy":
            if act.destination_path.exists():
                try:
                    act.destination_path.unlink()
                    restored += 1
                    candidate_empty_dirs.add(act.destination_path.parent)
                except OSError:
                    failed += 1
            else:
                failed += 1

    for p in sorted(candidate_empty_dirs, key=lambda d: len(d.parts), reverse=True):
        curr = p
        while curr.exists() and curr.is_dir() and not any(curr.iterdir()):
            try:
                curr.rmdir()
                cleaned_dirs.append(curr)
                curr = curr.parent
            except OSError:
                break

    history_manager.mark_session_undone(actual_id)
    return UndoResult(
        session_id=actual_id,
        restored_count=restored,
        failed_count=failed,
        cleaned_directories=cleaned_dirs,
    )


def clean_empty_directories(directory: Path, dry_run: bool = False) -> list[Path]:
    if not directory.is_dir():
        return []

    removed: list[Path] = []
    removed_set: set[Path] = set()

    for root, dirs, _ in os.walk(directory, topdown=False):
        for d in dirs:
            dir_path = Path(root) / d
            try:
                remaining_children = [
                    child for child in dir_path.iterdir()
                    if child not in removed_set
                ]
                if not remaining_children:
                    if not dry_run:
                        dir_path.rmdir()
                    removed.append(dir_path)
                    removed_set.add(dir_path)
            except OSError:
                continue
    return removed
