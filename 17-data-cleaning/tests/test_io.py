import json
from pathlib import Path
from cleanforge.io.flattener import flatten_dict, flatten_records
from cleanforge.io.reader import DatasetReader
from cleanforge.io.sniffer import detect_csv_dialect, detect_encoding
from cleanforge.io.writer import DatasetWriter


def test_flatten_dict() -> None:
    nested = {
        "user": {"name": "Alice", "address": {"city": "Paris"}},
        "tags": ["python", "data"],
    }
    flattened = flatten_dict(nested)
    assert flattened["user.name"] == "Alice"
    assert flattened["user.address.city"] == "Paris"
    assert flattened["tags"] == "python, data"


def test_flatten_records() -> None:
    records = [{"profile": {"age": 30}}, {"profile": {"age": 25}}]
    flat = flatten_records(records)
    assert flat[0]["profile.age"] == 30
    assert flat[1]["profile.age"] == 25


def test_detect_csv_dialect() -> None:
    sample_comma = "id,name,val\n1,alice,100\n2,bob,200"
    delim, quote, has_header = detect_csv_dialect(sample_comma)
    assert delim == ","
    assert has_header is True

    sample_semi = "id;name;val\n1;alice;100"
    delim_semi, _, _ = detect_csv_dialect(sample_semi)
    assert delim_semi == ";"


def test_reader_and_writer_csv(tmp_path: Path) -> None:
    file_path = tmp_path / "test.csv"
    data = [{"id": "1", "name": "Alice"}, {"id": "2", "name": "Bob"}]

    writer = DatasetWriter()
    writer.write(data, file_path)

    reader = DatasetReader()
    read_back = reader.read(file_path)

    assert len(read_back) == 2
    assert read_back[0]["name"] == "Alice"
    assert read_back[1]["name"] == "Bob"


def test_reader_and_writer_json(tmp_path: Path) -> None:
    file_path = tmp_path / "test.json"
    data = [
        {"id": 10, "details": {"score": 98}},
        {"id": 20, "details": {"score": 85}},
    ]

    writer = DatasetWriter()
    writer.write(data, file_path)

    reader = DatasetReader()
    read_back = reader.read(file_path, flatten=True)

    assert len(read_back) == 2
    assert read_back[0]["details.score"] == 98
    assert read_back[1]["details.score"] == 85


def test_reader_and_writer_jsonl(tmp_path: Path) -> None:
    file_path = tmp_path / "test.jsonl"
    data = [{"id": 1, "item": "book"}, {"id": 2, "item": "pen"}]

    writer = DatasetWriter()
    writer.write(data, file_path)

    reader = DatasetReader()
    read_back = reader.read(file_path)

    assert len(read_back) == 2
    assert read_back[0]["item"] == "book"
    assert read_back[1]["item"] == "pen"


def test_detect_encoding(tmp_path: Path) -> None:
    utf8_file = tmp_path / "utf8.txt"
    utf8_file.write_text("Hello World", encoding="utf-8")
    assert detect_encoding(utf8_file) in ["utf-8", "utf-8-sig"]


def test_reader_and_writer_tsv(tmp_path: Path) -> None:
    file_path = tmp_path / "test.tsv"
    data = [{"col1": "val1", "col2": "val2"}]

    writer = DatasetWriter()
    writer.write(data, file_path)

    reader = DatasetReader()
    read_back = reader.read(file_path)

    assert len(read_back) == 1
    assert read_back[0]["col1"] == "val1"
    assert read_back[0]["col2"] == "val2"


def test_pipe_delimited_csv(tmp_path: Path) -> None:
    file_path = tmp_path / "test_pipe.csv"
    file_path.write_text("id|title|price\n1|widget|10.5\n", encoding="utf-8")

    reader = DatasetReader()
    records = reader.read(file_path)

    assert len(records) == 1
    assert records[0]["title"] == "widget"
    assert records[0]["price"] == "10.5"


def test_recipe_save_and_load(tmp_path: Path) -> None:
    from cleanforge.config import get_preset_recipe, load_recipe_file, save_recipe_file

    recipe = get_preset_recipe("customer")
    yaml_path = tmp_path / "recipe.yaml"
    json_path = tmp_path / "recipe.json"

    save_recipe_file(recipe, yaml_path)
    save_recipe_file(recipe, json_path)

    loaded_yaml = load_recipe_file(yaml_path)
    loaded_json = load_recipe_file(json_path)

    assert loaded_yaml.name == "customer_cleaning_recipe"
    assert loaded_json.name == "customer_cleaning_recipe"
