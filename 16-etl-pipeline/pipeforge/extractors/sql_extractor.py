from collections.abc import Generator
from typing import Any
from sqlalchemy import create_engine, text
from pipeforge.extractors.base import BaseExtractor
from pipeforge.models.record import Record


class SqlExtractor(BaseExtractor):
    def __init__(
        self,
        connection_url: str,
        query: str,
        batch_size: int = 500,
    ):
        self.connection_url = connection_url
        self.query = query
        self.batch_size = batch_size
        self.engine = create_engine(self.connection_url)

    def extract(self) -> Generator[Record, None, None]:
        with self.engine.connect() as conn:
            result = conn.execution_options(stream_results=True).execute(text(self.query))
            row_number = 0
            while True:
                rows = result.fetchmany(self.batch_size)
                if not rows:
                    break
                for row in rows:
                    row_number += 1
                    row_dict = dict(row._mapping)
                    yield Record.from_raw(
                        raw=row_dict,
                        row_number=row_number,
                        metadata={
                            "source": self.connection_url,
                            "format": "sql",
                        },
                    )

    def get_metadata(self) -> dict[str, Any]:
        return {
            "extractor": "SqlExtractor",
            "connection_url": self.connection_url,
            "query": self.query,
        }
