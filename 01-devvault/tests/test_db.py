import json
from pathlib import Path
import pytest

from devvault.db import Database
from devvault.models import VaultItem


@pytest.fixture
def temp_db(tmp_path: Path) -> Database:
    db_file = tmp_path / "test_vault.db"
    return Database(db_file)


def test_add_and_get_item(temp_db: Database):
    item = VaultItem(
        title="Docker Prune All",
        item_type="command",
        content="docker system prune -a --volumes -f",
        description="Clean up everything in docker",
    )
    saved = temp_db.add_item(item)
    assert saved.id is not None
    assert saved.id > 0

    fetched = temp_db.get_item(saved.id)
    assert fetched is not None
    assert fetched.title == "Docker Prune All"
    assert fetched.item_type == "command"
    assert fetched.content == "docker system prune -a --volumes -f"
    assert fetched.description == "Clean up everything in docker"


def test_invalid_item_type():
    with pytest.raises(ValueError):
        VaultItem(
            title="Bad Item",
            item_type="unsupported",
            content="test",
        )


def test_list_items_and_filtering(temp_db: Database):
    temp_db.add_item(VaultItem(title="Python Snippet", item_type="snippet", content="print(1)"))
    temp_db.add_item(VaultItem(title="Bash Snippet", item_type="snippet", content="echo 1"))
    temp_db.add_item(VaultItem(title="Git Command", item_type="command", content="git status"))
    temp_db.add_item(VaultItem(title="Python Docs", item_type="url", content="https://python.org"))

    all_items = temp_db.list_items()
    assert len(all_items) == 4

    snippets = temp_db.list_items(item_type="snippet")
    assert len(snippets) == 2


def test_fts5_search(temp_db: Database):
    temp_db.add_item(VaultItem(
        title="FastAPI Hello World",
        item_type="snippet",
        content="from fastapi import FastAPI\napp = FastAPI()",
        language="python",
        description="web framework",
    ))
    temp_db.add_item(VaultItem(
        title="PostgreSQL Backup",
        item_type="command",
        content="pg_dump -U postgres mydb > backup.sql",
        description="database backup",
    ))
    temp_db.add_item(VaultItem(
        title="Quick Notes on Asyncio",
        item_type="note",
        content="Remember that async functions need an event loop to run.",
        description="python notes",
    ))

    res1 = temp_db.search_items("FastAPI")
    assert len(res1) == 1
    assert res1[0].title == "FastAPI Hello World"

    res2 = temp_db.search_items("backup.sql")
    assert len(res2) == 1
    assert res2[0].title == "PostgreSQL Backup"

    res3 = temp_db.search_items("FastAPI", item_type="command")
    assert len(res3) == 0

    res4 = temp_db.search_items("event")
    assert len(res4) == 1
    assert res4[0].item_type == "note"


def test_update_item(temp_db: Database):
    item = temp_db.add_item(VaultItem(
        title="Original Title",
        item_type="note",
        content="Original content",
    ))

    updated = temp_db.update_item(
        item.id,
        title="New Title",
        content="New content",
    )

    assert updated is not None
    assert updated.title == "New Title"
    assert updated.content == "New content"


def test_delete_item(temp_db: Database):
    item = temp_db.add_item(VaultItem(
        title="To Delete",
        item_type="note",
        content="Goodbye",
    ))

    assert temp_db.delete_item(item.id) is True
    assert temp_db.get_item(item.id) is None
    assert temp_db.delete_item(99999) is False


def test_stats(temp_db: Database):
    temp_db.add_item(VaultItem(title="S1", item_type="snippet", content="c1"))
    temp_db.add_item(VaultItem(title="C1", item_type="command", content="c2"))

    stats = temp_db.get_vault_stats()
    assert stats["total_items"] == 2
    assert stats["by_type"]["snippet"] == 1
    assert stats["by_type"]["command"] == 1


def test_export_and_import(temp_db: Database, tmp_path: Path):
    temp_db.add_item(VaultItem(title="Export 1", item_type="snippet", content="code()", language="python"))
    temp_db.add_item(VaultItem(title="Export 2", item_type="url", content="https://example.com"))

    json_str = temp_db.export_all("json")
    data = json.loads(json_str)
    assert len(data) == 2

    md_str = temp_db.export_all("markdown")
    assert "# DevVault Export" in md_str
    assert "Export 1" in md_str

    new_db = Database(tmp_path / "imported.db")
    count = new_db.import_all(data)
    assert count == 2
    assert len(new_db.list_items()) == 2
