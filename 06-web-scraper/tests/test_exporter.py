import csv
import json
import sqlite3
from web_scraper.exporter import DataExporter

SAMPLE_DATA = [
    {"id": 1, "name": "Item Alpha", "price": 19.99, "tags": ["sale", "new"]},
    {"id": 2, "name": "Item Beta", "price": 49.50, "tags": ["popular"]},
]


def test_export_json(tmp_path):
    target = tmp_path / "out.json"
    exported = DataExporter.export_json(SAMPLE_DATA, target)
    assert exported.exists()

    with open(exported, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    assert len(loaded) == 2
    assert loaded[0]["name"] == "Item Alpha"


def test_export_jsonl(tmp_path):
    target = tmp_path / "out.jsonl"
    exported = DataExporter.export_jsonl(SAMPLE_DATA, target)
    assert exported.exists()

    with open(exported, "r", encoding="utf-8") as f:
        lines = [json.loads(line) for line in f if line.strip()]
    assert len(lines) == 2
    assert lines[1]["id"] == 2


def test_export_csv(tmp_path):
    target = tmp_path / "out.csv"
    exported = DataExporter.export_csv(SAMPLE_DATA, target)
    assert exported.exists()

    with open(exported, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 2
    assert rows[0]["name"] == "Item Alpha"
    assert rows[0]["price"] == "19.99"


def test_export_markdown(tmp_path):
    target = tmp_path / "out.md"
    exported = DataExporter.export_markdown(SAMPLE_DATA, target)
    assert exported.exists()

    content = exported.read_text(encoding="utf-8")
    assert "| id | name | price | tags |" in content
    assert "| 1 | Item Alpha | 19.99 |" in content


def test_export_sqlite(tmp_path):
    target = tmp_path / "out.db"
    exported = DataExporter.export_sqlite(SAMPLE_DATA, target, table_name="test_items")
    assert exported.exists()

    with sqlite3.connect(exported) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, price FROM test_items")
        rows = cursor.fetchall()

    assert len(rows) == 2
    assert rows[0][1] == "Item Alpha"
    assert rows[0][2] == "19.99"


def test_export_by_format(tmp_path):
    target_csv = tmp_path / "test.csv"
    res = DataExporter.export_by_format(SAMPLE_DATA, target_csv)
    assert res.exists()
    assert res.suffix == ".csv"
