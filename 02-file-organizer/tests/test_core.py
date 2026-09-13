from pathlib import Path
from organizer.config import load_config
from organizer.core import (
    clean_empty_directories,
    execute_organization,
    execute_undo,
    plan_organization,
    resolve_collision,
    scan_directory,
)
from organizer.history import HistoryManager
from organizer.models import (
    ConflictResolution,
    OrganizeMode,
    OrganizeStrategy,
)


def test_scan_directory(tmp_path: Path):
    (tmp_path / 'doc.txt').write_text('content', encoding='utf-8')
    (tmp_path / '.hidden.txt').write_text('hidden', encoding='utf-8')
    sub = tmp_path / 'sub'
    sub.mkdir()
    (sub / 'nested.pdf').write_text('pdf', encoding='utf-8')

    shallow_items = scan_directory(tmp_path, recursive=False, include_hidden=False)
    assert len(shallow_items) == 1
    assert shallow_items[0].name == 'doc.txt'

    hidden_items = scan_directory(tmp_path, recursive=False, include_hidden=True)
    assert len(hidden_items) == 2

    recursive_items = scan_directory(tmp_path, recursive=True, include_hidden=False)
    assert len(recursive_items) == 2


def test_resolve_collision(tmp_path: Path):
    src = tmp_path / 'test.txt'
    src.write_text('source content', encoding='utf-8')
    dst = tmp_path / 'dest' / 'test.txt'
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text('existing content', encoding='utf-8')

    renamed_dst, reason = resolve_collision(dst, src, ConflictResolution.RENAME)
    assert renamed_dst == tmp_path / 'dest' / 'test (1).txt'

    skip_dst, reason = resolve_collision(dst, src, ConflictResolution.SKIP)
    assert skip_dst is None
    assert 'skipped' in reason

    overwrite_dst, reason = resolve_collision(dst, src, ConflictResolution.OVERWRITE)
    assert overwrite_dst == dst

    same_src = tmp_path / 'same.txt'
    same_src.write_text('identical', encoding='utf-8')
    same_dst = tmp_path / 'same_copy.txt'
    same_dst.write_text('identical', encoding='utf-8')
    hash_dst, hash_reason = resolve_collision(same_dst, same_src, ConflictResolution.HASH_CHECK)
    assert hash_dst is None
    assert 'Identical' in hash_reason


def test_organize_move_and_undo_workflow(tmp_path: Path):
    work_dir = tmp_path / 'work'
    work_dir.mkdir()
    img_file = work_dir / 'vacation.jpg'
    img_file.write_text('image-data', encoding='utf-8')
    doc_file = work_dir / 'notes.txt'
    doc_file.write_text('notes-data', encoding='utf-8')

    config = load_config()
    db_file = tmp_path / 'history.db'
    history_mgr = HistoryManager(db_file)

    actions = plan_organization(
        source_dir=work_dir,
        strategy=OrganizeStrategy.CATEGORY,
        config=config,
        mode=OrganizeMode.MOVE,
    )
    assert len(actions) == 2

    dry_result = execute_organization(
        actions=actions,
        mode=OrganizeMode.MOVE,
        dry_run=True,
        source_dir=work_dir,
        strategy='category',
        history_manager=history_mgr,
    )
    assert dry_result.moved_count == 2
    assert img_file.exists()
    assert doc_file.exists()

    live_result = execute_organization(
        actions=actions,
        mode=OrganizeMode.MOVE,
        dry_run=False,
        source_dir=work_dir,
        strategy='category',
        history_manager=history_mgr,
    )
    assert live_result.moved_count == 2
    assert not img_file.exists()
    assert not doc_file.exists()
    assert (work_dir / 'Images' / 'vacation.jpg').exists()
    assert (work_dir / 'Documents' / 'notes.txt').exists()

    undo_res = execute_undo(history_mgr, live_result.session_id)
    assert undo_res is not None
    assert undo_res.restored_count == 2
    assert img_file.exists()
    assert doc_file.exists()
    assert not (work_dir / 'Images').exists()
    assert not (work_dir / 'Documents').exists()


def test_organize_copy_mode_and_undo(tmp_path: Path):
    work_dir = tmp_path / 'copy_work'
    work_dir.mkdir()
    song = work_dir / 'track.mp3'
    song.write_text('audio', encoding='utf-8')

    config = load_config()
    db_file = tmp_path / 'history_copy.db'
    history_mgr = HistoryManager(db_file)

    actions = plan_organization(
        source_dir=work_dir,
        strategy=OrganizeStrategy.CATEGORY,
        config=config,
        mode=OrganizeMode.COPY,
    )
    res = execute_organization(
        actions=actions,
        mode=OrganizeMode.COPY,
        dry_run=False,
        source_dir=work_dir,
        strategy='category',
        history_manager=history_mgr,
    )
    assert res.copied_count == 1
    assert song.exists()
    assert (work_dir / 'Audio' / 'track.mp3').exists()

    undo_res = execute_undo(history_mgr, res.session_id)
    assert undo_res is not None
    assert undo_res.restored_count == 1
    assert song.exists()
    assert not (work_dir / 'Audio' / 'track.mp3').exists()


def test_clean_empty_directories(tmp_path: Path):
    base = tmp_path / 'cleanup'
    empty_child = base / 'parent' / 'empty_child'
    empty_child.mkdir(parents=True)
    non_empty = base / 'keep'
    non_empty.mkdir()
    (non_empty / 'file.txt').write_text('keep', encoding='utf-8')

    dry_removed = clean_empty_directories(base, dry_run=True)
    assert len(dry_removed) == 2
    assert empty_child.exists()

    live_removed = clean_empty_directories(base, dry_run=False)
    assert len(live_removed) == 2
    assert not empty_child.exists()
    assert (non_empty / 'file.txt').exists()
