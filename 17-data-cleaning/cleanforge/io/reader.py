import csv
import json
from pathlib import Path
from typing import Any
from cleanforge.io.flattener import flatten_records
from cleanforge.io.sniffer import detect_csv_dialect, detect_encoding


class DatasetReader:
    def read(
        self,
        file_path: str | Path,
        delimiter: str | None = None,
        encoding: str | None = None,
        flatten: bool = True,
        nested_key: str | None = None,
    ) -> list[dict[str, Any]]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        suffix = path.suffix.lower()
        if suffix in [".csv", ".tsv", ".txt"]:
            return self._read_csv(path, delimiter=delimiter, encoding=encoding)
        elif suffix in [".json"]:
            return self._read_json(path, encoding=encoding, flatten=flatten, nested_key=nested_key)
        elif suffix in [".jsonl", ".ndjson"]:
            return self._read_jsonl(path, encoding=encoding, flatten=flatten)
        else:
            return self._read_csv(path, delimiter=delimiter, encoding=encoding)

    def _read_csv(
        self,
        path: Path,
        delimiter: str | None = None,
        encoding: str | None = None,
    ) -> list[dict[str, Any]]:
        chosen_encoding = encoding or detect_encoding(path)
        with open(path, "r", encoding=chosen_encoding, newline="") as f:
            sample = f.read(8192)
            f.seek(0)
            detected_delimiter, quotechar, _ = detect_csv_dialect(sample)
            final_delimiter = delimiter or (
                "\t" if path.suffix.lower() == ".tsv" else detected_delimiter
            )
            reader = csv.DictReader(f, delimiter=final_delimiter, quotechar=quotechar)
            rows: list[dict[str, Any]] = []
            for row in reader:
                cleaned_row = {
                    (k.strip() if k is not None else ""): v
                    for k, v in row.items()
                    if k is not None
                }
                rows.append(cleaned_row)
            return rows

    def _read_json(
        self,
        path: Path,
        encoding: str | None = None,
        flatten: bool = True,
        nested_key: str | None = None,
    ) -> list[dict[str, Any]]:
        chosen_encoding = encoding or detect_encoding(path)
        with open(path, "r", encoding=chosen_encoding) as f:
            raw_data = json.load(f)

        records: list[dict[str, Any]] = []
        if isinstance(raw_data, list):
            records = [item for item in raw_data if isinstance(item, dict)]
        elif isinstance(raw_data, dict):
            if nested_key and nested_key in raw_data and isinstance(raw_data[nested_key], list):
                records = [item for item in raw_data[nested_key] if isinstance(item, dict)]
            else:
                for candidate in ["data", "records", "items", "results", "rows"]:
                    if candidate in raw_data and isinstance(raw_data[candidate], list):
                        records = [item for item in raw_data[candidate] if isinstance(item, dict)]
                        break
                if not records:
                    records = [raw_data]

        if flatten:
            return flatten_records(records)
        return records

    def _read_jsonl(
        self,
        path: Path,
        encoding: str | None = None,
        flatten: bool = True,
    ) -> list[dict[str, Any]]:
        chosen_encoding = encoding or detect_encoding(path)
        records: list[dict[str, Any]] = []
        with open(path, "r", encoding=chosen_encoding) as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    obj = json.loads(line_str)
                    if isinstance(obj, dict):
                        records.append(obj)
                except json.JSONDecodeError:
                    continue

        if flatten:
            return flatten_records(records)
        return records
