import hashlib
from collections import defaultdict
from pathlib import Path
from organizer.models import DuplicateGroup


def compute_file_hash(file_path: Path, chunk_size: int = 65536) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as stream:
        while chunk := stream.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def find_duplicates(
    directory: Path,
    recursive: bool = True,
    min_size: int = 0,
    ignored_patterns: list[str] | None = None,
) -> list[DuplicateGroup]:
    if not directory.is_dir():
        return []

    size_map: dict[int, list[Path]] = defaultdict(list)
    search_iter = directory.rglob("*") if recursive else directory.glob("*")

    for entry in search_iter:
        if not entry.is_file() or entry.is_symlink():
            continue
        try:
            stat_info = entry.stat()
            file_size = stat_info.st_size
            if file_size >= min_size:
                size_map[file_size].append(entry)
        except OSError:
            continue

    potential_groups = [paths for paths in size_map.values() if len(paths) > 1]
    duplicate_groups: list[DuplicateGroup] = []

    for path_list in potential_groups:
        hash_map: dict[str, list[Path]] = defaultdict(list)
        for path in path_list:
            try:
                file_hash = compute_file_hash(path)
                hash_map[file_hash].append(path)
            except OSError:
                continue

        for file_hash, identical_paths in hash_map.items():
            if len(identical_paths) > 1:
                sorted_by_mtime = sorted(
                    identical_paths,
                    key=lambda p: p.stat().st_mtime if p.exists() else 0,
                )
                duplicate_groups.append(
                    DuplicateGroup(
                        size=sorted_by_mtime[0].stat().st_size,
                        checksum=file_hash,
                        original=sorted_by_mtime[0],
                        duplicates=sorted_by_mtime[1:],
                    )
                )

    duplicate_groups.sort(key=lambda g: g.size * len(g.duplicates), reverse=True)
    return duplicate_groups
