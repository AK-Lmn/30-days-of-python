import csv
import json
from pathlib import Path
from typing import Any


class DatasetWriter:
    def write(
        self,
        records: list[dict[str, Any]],
        file_path: str | Path,
        format_type: str | None = None,
        encoding: str = "utf-8",
    ) -> None:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        chosen_format = (
            format_type.lower() if format_type else path.suffix.lower().lstrip(".")
        )

        if chosen_format in ["csv", "txt"]:
            self._write_csv(records, path, delimiter=",", encoding=encoding)
        elif chosen_format in ["tsv"]:
            self._write_csv(records, path, delimiter="\t", encoding=encoding)
        elif chosen_format in ["json"]:
            self._write_json(records, path, encoding=encoding)
        elif chosen_format in ["jsonl", "ndjson"]:
            self._write_jsonl(records, path, encoding=encoding)
        else:
            self._write_csv(records, path, delimiter=",", encoding=encoding)

    def _write_csv(
        self,
        records: list[dict[str, Any]],
        path: Path,
        delimiter: str = ",",
        encoding: str = "utf-8",
    ) -> None:
        if not records:
            with open(path, "w", encoding=encoding, newline="") as f:
                f.write("")
            return

        fieldnames: list[str] = []
        for r in records:
            for k in r.keys():
                if k not in fieldnames:
                    fieldnames.append(k)

        with open(path, "w", encoding=encoding, newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=fieldnames,
                delimiter=delimiter,
                extrasaction="ignore",
            )
            writer.writeheader()
            for r in records:
                sanitized = {k: ("" if v is None else v) for k, v in r.items()}
                writer.writerow(sanitized)

    def _write_json(
        self,
        records: list[dict[str, Any]],
        path: Path,
        encoding: str = "utf-8",
    ) -> None:
        with open(path, "w", encoding=encoding) as f:
            json.dump(records, f, indent=2, default=str)

    def _write_jsonl(
        self,
        records: list[dict[str, Any]],
        path: Path,
        encoding: str = "utf-8",
    ) -> None:
        with open(path, "w", encoding=encoding) as f:
            for r in records:
                line = json.dumps(r, default=str)
                f.write(line + "\n")
