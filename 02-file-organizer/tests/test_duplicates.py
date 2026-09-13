import hashlib
from pathlib import Path
from organizer.duplicates import compute_file_hash, find_duplicates


def test_compute_file_hash(tmp_path: Path):
    sample = tmp_path / 'sample.txt'
    sample.write_text('Antigravity file organizer test', encoding='utf-8')
    expected = hashlib.sha256('Antigravity file organizer test'.encode('utf-8')).hexdigest()
    assert compute_file_hash(sample) == expected


def test_find_duplicates(tmp_path: Path):
    f1 = tmp_path / 'file1.txt'
    f2 = tmp_path / 'file2.txt'
    f3 = tmp_path / 'unique.txt'

    content_dup = 'Exact identical content'
    f1.write_text(content_dup, encoding='utf-8')
    f2.write_text(content_dup, encoding='utf-8')
    f3.write_text('Different content entirely', encoding='utf-8')

    groups = find_duplicates(tmp_path, recursive=False)
    assert len(groups) == 1
    group = groups[0]
    assert group.size == len(content_dup.encode('utf-8'))
    assert len(group.duplicates) == 1
    assert group.original.name in ['file1.txt', 'file2.txt']
    assert group.duplicates[0].name in ['file1.txt', 'file2.txt']
    assert group.original.name != group.duplicates[0].name


def test_find_duplicates_empty_directory(tmp_path: Path):
    assert find_duplicates(tmp_path) == []
