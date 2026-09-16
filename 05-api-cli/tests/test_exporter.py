import json
from pathlib import Path
from api_cli.exporter import (
    data_to_csv_str,
    data_to_json_str,
    data_to_markdown_str,
    export_data,
)


def test_data_to_json_str():
    data = {"id": 1, "name": "Item"}
    res = data_to_json_str(data)
    assert json.loads(res) == data


def test_data_to_csv_str():
    data = [
        {"id": 1, "name": "Alice", "tags": ["admin", "dev"]},
        {"id": 2, "name": "Bob", "tags": ["user"]},
    ]
    csv_out = data_to_csv_str(data)
    lines = csv_out.strip().split("\n")
    assert lines[0] == "id,name,tags"
    assert "Alice" in lines[1]
    assert "Bob" in lines[2]


def test_data_to_markdown_str():
    data = [
        {"id": 1, "status": "active"},
        {"id": 2, "status": "pending"},
    ]
    md_out = data_to_markdown_str(data)
    assert "| id | status |" in md_out
    assert "| --- | --- |" in md_out
    assert "| 1 | active |" in md_out


def test_export_data(tmp_path):
    data = [{"title": "Post 1"}, {"title": "Post 2"}]

    json_file = tmp_path / "out.json"
    export_data(data, json_file)
    assert json_file.exists()
    assert json.loads(json_file.read_text(encoding="utf-8")) == data

    csv_file = tmp_path / "out.csv"
    export_data(data, csv_file)
    assert csv_file.exists()
    assert "Post 1" in csv_file.read_text(encoding="utf-8")

    md_file = tmp_path / "out.md"
    export_data(data, md_file)
    assert md_file.exists()
    assert "| title |" in md_file.read_text(encoding="utf-8")
