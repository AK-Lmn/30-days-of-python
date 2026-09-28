import json
import sqlite3
from pathlib import Path
import httpx
import pytest
import respx
from pipeforge.extractors.csv_extractor import CsvExtractor
from pipeforge.extractors.json_extractor import JsonExtractor
from pipeforge.extractors.sql_extractor import SqlExtractor
from pipeforge.extractors.api_extractor import ApiExtractor


def test_csv_extractor_basic(tmp_path: Path) -> None:
    csv_file = tmp_path / "data.csv"
    csv_file.write_text("id,name,age\n1,Alice,30\n2,Bob,25\n", encoding="utf-8")

    extractor = CsvExtractor(csv_file)
    records = list(extractor.extract())

    assert len(records) == 2
    assert records[0].data == {"id": "1", "name": "Alice", "age": "30"}
    assert records[1].data == {"id": "2", "name": "Bob", "age": "25"}
    assert extractor.get_total_count() == 2


def test_csv_extractor_delimiter_detection(tmp_path: Path) -> None:
    tsv_file = tmp_path / "data.tsv"
    tsv_file.write_text("id\tname\tcity\n101\tCharlie\tSeattle\n", encoding="utf-8")

    extractor = CsvExtractor(tsv_file)
    records = list(extractor.extract())

    assert len(records) == 1
    assert records[0].data["name"] == "Charlie"
    assert records[0].data["city"] == "Seattle"


def test_json_extractor_array(tmp_path: Path) -> None:
    json_file = tmp_path / "users.json"
    data = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    json_file.write_text(json.dumps(data), encoding="utf-8")

    extractor = JsonExtractor(json_file)
    records = list(extractor.extract())

    assert len(records) == 2
    assert records[0].data["name"] == "Alice"


def test_json_extractor_lines(tmp_path: Path) -> None:
    jsonl_file = tmp_path / "users.jsonl"
    jsonl_file.write_text('{"id": 10, "val": "A"}\n{"id": 20, "val": "B"}\n', encoding="utf-8")

    extractor = JsonExtractor(jsonl_file, lines=True)
    records = list(extractor.extract())

    assert len(records) == 2
    assert records[1].data["val"] == "B"
    assert extractor.get_total_count() == 2


def test_json_extractor_nested_root(tmp_path: Path) -> None:
    json_file = tmp_path / "nested.json"
    data = {"status": "ok", "items": [{"code": "XYZ"}, {"code": "ABC"}]}
    json_file.write_text(json.dumps(data), encoding="utf-8")

    extractor = JsonExtractor(json_file, root_key="items")
    records = list(extractor.extract())

    assert len(records) == 2
    assert records[0].data["code"] == "XYZ"


def test_sql_extractor(tmp_path: Path) -> None:
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()
    cur.execute("CREATE TABLE products (id INT, title TEXT, price REAL)")
    cur.execute("INSERT INTO products VALUES (1, 'Widget', 19.99)")
    cur.execute("INSERT INTO products VALUES (2, 'Gadget', 29.99)")
    conn.commit()
    conn.close()

    extractor = SqlExtractor(
        connection_url=f"sqlite:///{db_file}",
        query="SELECT id, title, price FROM products ORDER BY id",
    )
    records = list(extractor.extract())

    assert len(records) == 2
    assert records[0].data["title"] == "Widget"
    assert records[1].data["price"] == 29.99


@respx.mock
def test_api_extractor() -> None:
    respx.get("https://api.example.com/items?page=1&per_page=2").respond(
        200,
        json={"data": [{"id": 1, "item": "A"}, {"id": 2, "item": "B"}]},
    )
    respx.get("https://api.example.com/items?page=2&per_page=2").respond(
        200,
        json={"data": [{"id": 3, "item": "C"}]},
    )

    extractor = ApiExtractor(
        endpoint_url="https://api.example.com/items",
        pagination_type="page",
        page_size=2,
        data_key="data",
    )
    records = list(extractor.extract())

    assert len(records) == 3
    assert [r.data["item"] for r in records] == ["A", "B", "C"]
