from datetime import datetime
from pathlib import Path
from organizer.models import (
    CustomRule,
    FileItem,
    OrganizerConfig,
    OrganizeStrategy,
)
from organizer.rules import (
    get_category_for_extension,
    get_size_tier,
    is_ignored_dir,
    is_ignored_file,
    match_custom_rule,
    resolve_relative_destination,
)


def test_is_ignored_file():
    ignored = ['.*', 'desktop.ini', 'thumbs.db']
    assert is_ignored_file('.env', ignored) is True
    assert is_ignored_file('.DS_Store', ignored) is True
    assert is_ignored_file('thumbs.db', ignored) is True
    assert is_ignored_file('notes.txt', ignored) is False
    assert is_ignored_file('photo.png', ignored) is False


def test_is_ignored_dir():
    ignored = ['.git', '.venv', 'node_modules']
    assert is_ignored_dir('.git', ignored) is True
    assert is_ignored_dir('node_modules', ignored) is True
    assert is_ignored_dir('Documents', ignored) is False
    assert is_ignored_dir('src', ignored) is False


def test_get_category_for_extension():
    categories = {
        'Images': ['.jpg', '.png'],
        'Documents': ['.pdf', '.txt'],
    }
    assert get_category_for_extension('.jpg', categories) == 'Images'
    assert get_category_for_extension('.PNG', categories) == 'Images'
    assert get_category_for_extension('.pdf', categories) == 'Documents'
    assert get_category_for_extension('.unknown', categories) == 'Other'


def test_get_size_tier():
    assert get_size_tier(500 * 1024) == 'Tiny (<1MB)'
    assert get_size_tier(5 * 1024 * 1024) == 'Small (1-10MB)'
    assert get_size_tier(50 * 1024 * 1024) == 'Medium (10-100MB)'
    assert get_size_tier(500 * 1024 * 1024) == 'Large (100MB-1GB)'
    assert get_size_tier(2 * 1024 * 1024 * 1024) == 'Huge (>1GB)'


def test_match_custom_rule():
    rules = [
        CustomRule(
            name='Invoices',
            folder='Finance/Invoices',
            pattern=r'(?i)^inv.*\.pdf$',
        ),
        CustomRule(
            name='Heavy Files',
            folder='LargeFiles',
            min_size=1000000,
        ),
    ]

    item_match = FileItem(
        path=Path('INV_2026_01.pdf'),
        name='INV_2026_01.pdf',
        extension='.pdf',
        size=5000,
        modified_at=datetime.now(),
        created_at=datetime.now(),
    )
    assert match_custom_rule(item_match, rules) == 'Finance/Invoices'

    item_heavy = FileItem(
        path=Path('video.mp4'),
        name='video.mp4',
        extension='.mp4',
        size=2000000,
        modified_at=datetime.now(),
        created_at=datetime.now(),
    )
    assert match_custom_rule(item_heavy, rules) == 'LargeFiles'

    item_no_match = FileItem(
        path=Path('regular.txt'),
        name='regular.txt',
        extension='.txt',
        size=100,
        modified_at=datetime.now(),
        created_at=datetime.now(),
    )
    assert match_custom_rule(item_no_match, rules) is None


def test_resolve_relative_destination():
    config = OrganizerConfig(
        categories={'Images': ['.jpg', '.png'], 'Documents': ['.pdf']},
        rules=[
            CustomRule(name='Invoices', folder='Finance/Invoices', pattern=r'(?i)^inv')
        ],
    )
    test_time = datetime(2026, 9, 13, 15, 30)

    invoice_item = FileItem(
        path=Path('invoice_101.pdf'),
        name='invoice_101.pdf',
        extension='.pdf',
        size=1024,
        modified_at=test_time,
        created_at=test_time,
    )
    cat, dest = resolve_relative_destination(invoice_item, OrganizeStrategy.CATEGORY, config)
    assert cat == 'Custom'
    assert dest == Path('Finance/Invoices/invoice_101.pdf')

    photo_item = FileItem(
        path=Path('photo.jpg'),
        name='photo.jpg',
        extension='.jpg',
        size=1024,
        modified_at=test_time,
        created_at=test_time,
    )
    cat, dest = resolve_relative_destination(photo_item, OrganizeStrategy.CATEGORY, config)
    assert cat == 'Images'
    assert dest == Path('Images/photo.jpg')

    cat, dest_ext = resolve_relative_destination(photo_item, OrganizeStrategy.EXTENSION, config)
    assert cat == 'JPG'
    assert dest_ext == Path('JPG/photo.jpg')

    cat, dest_date = resolve_relative_destination(photo_item, OrganizeStrategy.DATE, config)
    assert cat == '2026/2026-09'
    assert dest_date == Path('2026/2026-09/photo.jpg')
