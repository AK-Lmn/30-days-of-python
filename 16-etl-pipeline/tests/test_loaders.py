import json
import sqlite3
from pathlib import Path
import respx
from pipeforge.loaders.csv_loader import CsvLoader
from pipeforge.loaders.json_loader import JsonLoader
from pipeforge.loaders.database_loader import DatabaseLoader
from pipeforge.loaders.api_loader import ApiLoader
from pipeforge.models.record import Record
from pipeforge.models.enums import LoadMode


def test_csv_loader(tmp_path: Path) -> None:
    csv_file = tmp_path / "output.csv"
    loader = CsvLoader(csv_file, mode=LoadMode.REPLACE)
    loader.initialize()

    records = [
        Record.from_raw({"id": 1, "name": "Alice"}),
        Record.from_raw({"id": 2, "name": "Bob"}),
    ]
    loaded = loader.load(records)
    loader.finalize()

    assert loaded == 2
    assert csv_file.exists()
    content = csv_file.read_text(encoding="utf-8").strip().splitlines()
    assert content[0] == "id,name"
    assert content[1] == "1,Alice"
    assert content[2] == "2,Bob"


def test_json_loader(tmp_path: Path) -> None:
    json_file = tmp_path / "output.json"
    loader = JsonLoader(json_file, lines=False, mode=LoadMode.REPLACE)
    loader.initialize()

    records = [Record.from_raw({"id": 10, "val": "A"})]
    loader.load(records)
    loader.finalize()

    data = json.loads(json_file.read_text(encoding="utf-8"))
    assert len(data) == 1
    assert data[0]["val"] == "A"


def test_jsonl_loader(tmp_path: Path) -> None:
    jsonl_file = tmp_path / "output.jsonl"
    loader = JsonLoader(jsonl_file, lines=True, mode=LoadMode.REPLACE)
    loader.initialize()

    records = [
        Record.from_raw({"id": 1, "tag": "X"}),
        Record.from_raw({"id": 2, "tag": "Y"}),
    ]
    loader.load(records)
    loader.finalize()

    lines = [json.loads(line) for line in jsonl_file.read_text(encoding="utf-8").strip().splitlines()]
    assert len(lines) == 2
    assert lines[1]["tag"] == "Y"


def test_database_loader_append_and_replace(tmp_path: Path) -> None:
    db_file = tmp_path / "store.db"
    url = f"sqlite:///{db_file}"

    loader1 = DatabaseLoader(url, table_name="users", mode=LoadMode.REPLACE)
    loader1.initialize()
    loader1.load([Record.from_raw({"id": 1, "name": "User 1"})])
    loader1.finalize()

    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM users")
    assert cur.fetchone()[0] == 1
    conn.close()

    loader2 = DatabaseLoader(url, table_name="users", mode=LoadMode.APPEND)
    loader2.initialize()
    loader2.load([Record.from_raw({"id": 2, "name": "User 2"})])
    loader2.finalize()

    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM users")
    assert cur.fetchone()[0] == 2
    conn.close()


def test_database_loader_upsert(tmp_path: Path) -> None:
    db_file = tmp_path / "upsert.db"
    url = f"sqlite:///{db_file}"

    loader = DatabaseLoader(url, table_name="products", mode=LoadMode.UPSERT, primary_keys=["id"])
    loader.initialize()
    loader.load([Record.from_raw({"id": 1, "name": "Initial", "price": 10.0})])
    loader.load([Record.from_raw({"id": 1, "name": "Updated", "price": 15.0})])
    loader.finalize()

    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute("SELECT id, name, price FROM products")
    row = cur.fetchone()
    assert row[0] == 1
    assert row[1] == "Updated"
    assert row[2] == 15.0
    assert cur.fetchone() is None
    conn.close()


@respx.mock
def test_api_loader() -> None:
    mock_route = respx.post("https://api.example.com/dest").respond(200, json={"status": "ok"})
    loader = ApiLoader(endpoint_url="https://api.example.com/dest")
    records = [Record.from_raw({"id": 100, "event": "click"})]
    loaded = loader.load(records)
    assert loaded == 1
    assert mock_route.called
