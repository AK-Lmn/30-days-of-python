import csv
from pathlib import Path
from typing import Any
from pipeforge.loaders.base import BaseLoader
from pipeforge.models.enums import LoadMode
from pipeforge.models.record import Record


class CsvLoader(BaseLoader):
    def __init__(
        self,
        file_path: Path | str,
        mode: LoadMode = LoadMode.REPLACE,
        delimiter: str = ",",
        encoding: str = "utf-8",
    ):
        self.file_path = Path(file_path)
        self.mode = mode
        self.delimiter = delimiter
        self.encoding = encoding
        self._headers_written = False

    def initialize(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if self.mode == LoadMode.REPLACE and self.file_path.exists():
            self.file_path.unlink()
        elif self.mode == LoadMode.APPEND and self.file_path.exists() and self.file_path.stat().st_size > 0:
            self._headers_written = True

    def load(self, records: list[Record]) -> int:
        if not records:
            return 0

        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = list(records[0].data.keys())

        write_header = not self._headers_written
        if not self.file_path.exists() or self.file_path.stat().st_size == 0:
            write_header = True

        mode_str = "a" if self.mode == LoadMode.APPEND else ("a" if self._headers_written else "w")

        with open(self.file_path, mode=mode_str, encoding=self.encoding, newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=fieldnames,
                delimiter=self.delimiter,
                extrasaction="ignore",
            )
            if write_header:
                writer.writeheader()
                self._headers_written = True

            for r in records:
                writer.writerow(r.data)
                r.mark_loaded()

        return len(records)

    def get_metadata(self) -> dict[str, Any]:
        return {
            "loader": "CsvLoader",
            "file_path": str(self.file_path),
            "mode": self.mode.value,
        }
