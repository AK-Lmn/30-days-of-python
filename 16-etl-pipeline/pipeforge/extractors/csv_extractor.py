import csv
from collections.abc import Generator
from pathlib import Path
from typing import Any
from pipeforge.extractors.base import BaseExtractor
from pipeforge.models.record import Record


class CsvExtractor(BaseExtractor):
    def __init__(
        self,
        file_path: Path | str,
        delimiter: str | None = None,
        encoding: str = "utf-8",
        skip_rows: int = 0,
    ):
        self.file_path = Path(file_path)
        self.delimiter = delimiter
        self.encoding = encoding
        self.skip_rows = skip_rows

    def _detect_delimiter(self, sample_text: str) -> str:
        if self.delimiter:
            return self.delimiter
        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample_text)
            return dialect.delimiter
        except Exception:
            return ","

    def extract(self) -> Generator[Record, None, None]:
        if not self.file_path.exists():
            raise FileNotFoundError(f"Source file not found: {self.file_path}")

        with open(self.file_path, mode="r", encoding=self.encoding, errors="replace", newline="") as f:
            for _ in range(self.skip_rows):
                f.readline()

            sample_pos = f.tell()
            sample_text = f.read(4096)
            f.seek(sample_pos)

            actual_delimiter = self._detect_delimiter(sample_text)
            reader = csv.DictReader(f, delimiter=actual_delimiter)

            if reader.fieldnames:
                reader.fieldnames = [name.strip() for name in reader.fieldnames if name is not None]

            row_number = 0
            for row in reader:
                row_number += 1
                cleaned_row = {
                    k: (v.strip() if isinstance(v, str) else v)
                    for k, v in row.items()
                    if k is not None
                }
                yield Record.from_raw(
                    raw=cleaned_row,
                    row_number=row_number,
                    metadata={"source": str(self.file_path), "format": "csv"},
                )

    def get_total_count(self) -> int | None:
        if not self.file_path.exists():
            return None
        with open(self.file_path, mode="r", encoding=self.encoding, errors="replace") as f:
            lines = sum(1 for _ in f)
        return max(0, lines - 1 - self.skip_rows)

    def get_metadata(self) -> dict[str, Any]:
        return {
            "extractor": "CsvExtractor",
            "file_path": str(self.file_path),
            "encoding": self.encoding,
            "delimiter": self.delimiter,
        }
