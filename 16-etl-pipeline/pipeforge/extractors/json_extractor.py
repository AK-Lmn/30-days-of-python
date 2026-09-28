import json
from collections.abc import Generator
from pathlib import Path
from typing import Any
from pipeforge.extractors.base import BaseExtractor
from pipeforge.models.record import Record


class JsonExtractor(BaseExtractor):
    def __init__(
        self,
        file_path: Path | str,
        lines: bool = False,
        root_key: str | None = None,
        encoding: str = "utf-8",
    ):
        self.file_path = Path(file_path)
        self.lines = lines or self.file_path.suffix.lower() == ".jsonl"
        self.root_key = root_key
        self.encoding = encoding

    def extract(self) -> Generator[Record, None, None]:
        if not self.file_path.exists():
            raise FileNotFoundError(f"Source file not found: {self.file_path}")

        row_number = 0
        if self.lines:
            with open(self.file_path, mode="r", encoding=self.encoding, errors="replace") as f:
                for line in f:
                    line_str = line.strip()
                    if not line_str:
                        continue
                    row_number += 1
                    item = json.loads(line_str)
                    if isinstance(item, dict):
                        yield Record.from_raw(
                            raw=item,
                            row_number=row_number,
                            metadata={"source": str(self.file_path), "format": "jsonl"},
                        )
        else:
            with open(self.file_path, mode="r", encoding=self.encoding, errors="replace") as f:
                payload = json.load(f)

            items: list[Any] = []
            if isinstance(payload, list):
                items = payload
            elif isinstance(payload, dict):
                if self.root_key and self.root_key in payload:
                    val = payload[self.root_key]
                    if isinstance(val, list):
                        items = val
                    else:
                        items = [val]
                else:
                    for key in ["data", "items", "results", "records"]:
                        if key in payload and isinstance(payload[key], list):
                            items = payload[key]
                            break
                    if not items:
                        items = [payload]

            for item in items:
                if isinstance(item, dict):
                    row_number += 1
                    yield Record.from_raw(
                        raw=item,
                        row_number=row_number,
                        metadata={"source": str(self.file_path), "format": "json"},
                    )

    def get_total_count(self) -> int | None:
        if not self.file_path.exists():
            return None
        if self.lines:
            with open(self.file_path, mode="r", encoding=self.encoding, errors="replace") as f:
                return sum(1 for line in f if line.strip())
        return None

    def get_metadata(self) -> dict[str, Any]:
        return {
            "extractor": "JsonExtractor",
            "file_path": str(self.file_path),
            "lines": self.lines,
            "root_key": self.root_key,
        }
