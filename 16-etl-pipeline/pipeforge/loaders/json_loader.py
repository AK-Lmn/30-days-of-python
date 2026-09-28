import json
from pathlib import Path
from typing import Any
from pipeforge.loaders.base import BaseLoader
from pipeforge.models.enums import LoadMode
from pipeforge.models.record import Record


class JsonLoader(BaseLoader):
    def __init__(
        self,
        file_path: Path | str,
        lines: bool = False,
        mode: LoadMode = LoadMode.REPLACE,
        indent: int = 2,
        encoding: str = "utf-8",
    ):
        self.file_path = Path(file_path)
        self.lines = lines or self.file_path.suffix.lower() == ".jsonl"
        self.mode = mode
        self.indent = indent
        self.encoding = encoding
        self._buffered_records: list[dict[str, Any]] = []

    def initialize(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if self.mode == LoadMode.REPLACE and self.file_path.exists():
            self.file_path.unlink()
        elif self.mode == LoadMode.APPEND and not self.lines and self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding=self.encoding) as f:
                    self._buffered_records = json.load(f)
            except Exception:
                self._buffered_records = []

    def load(self, records: list[Record]) -> int:
        if not records:
            return 0

        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        row_dicts = [r.data for r in records]

        if self.lines:
            write_mode = "a" if self.mode == LoadMode.APPEND else "w"
            with open(self.file_path, mode=write_mode, encoding=self.encoding) as f:
                for row in row_dicts:
                    f.write(json.dumps(row, default=str) + "\n")
        else:
            self._buffered_records.extend(row_dicts)

        for r in records:
            r.mark_loaded()

        return len(records)

    def finalize(self) -> None:
        if not self.lines and self._buffered_records:
            with open(self.file_path, mode="w", encoding=self.encoding) as f:
                json.dump(self._buffered_records, f, indent=self.indent, default=str)

    def get_metadata(self) -> dict[str, Any]:
        return {
            "loader": "JsonLoader",
            "file_path": str(self.file_path),
            "lines": self.lines,
            "mode": self.mode.value,
        }
