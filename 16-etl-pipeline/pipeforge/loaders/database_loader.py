import json
from typing import Any
from sqlalchemy import (
    Boolean,
    Column,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    inspect,
)
from sqlalchemy.dialects.sqlite import insert as sqlite_upsert
from pipeforge.loaders.base import BaseLoader
from pipeforge.models.enums import LoadMode
from pipeforge.models.record import Record


class DatabaseLoader(BaseLoader):
    def __init__(
        self,
        connection_url: str,
        table_name: str,
        mode: LoadMode = LoadMode.APPEND,
        primary_keys: list[str] | None = None,
    ):
        self.connection_url = connection_url
        self.table_name = table_name
        self.mode = mode
        self.primary_keys = primary_keys or []
        self.engine = create_engine(self.connection_url)
        self.metadata = MetaData()
        self.table: Table | None = None
        self._table_initialized = False

    def _infer_column_type(self, val: Any) -> Any:
        if isinstance(val, bool):
            return Boolean
        if isinstance(val, int):
            return Integer
        if isinstance(val, float):
            return Float
        if isinstance(val, (dict, list)):
            return Text
        return String(255)

    def _ensure_table(self, sample_data: dict[str, Any]) -> Table:
        inspector = inspect(self.engine)
        if inspector.has_table(self.table_name):
            if self.mode == LoadMode.REPLACE and not self._table_initialized:
                with self.engine.begin() as conn:
                    self.metadata.reflect(bind=self.engine)
                    existing_tbl = self.metadata.tables.get(self.table_name)
                    if existing_tbl is not None:
                        existing_tbl.drop(conn)
                    self.metadata.clear()
            else:
                self.metadata.reflect(bind=self.engine)
                tbl = self.metadata.tables[self.table_name]
                self._table_initialized = True
                return tbl

        columns = []
        for col_name, val in sample_data.items():
            is_pk = col_name in self.primary_keys
            col_type = self._infer_column_type(val)
            columns.append(Column(col_name, col_type, primary_key=is_pk))

        if not any(c.primary_key for c in columns) and self.primary_keys:
            for pk in self.primary_keys:
                if pk not in sample_data:
                    columns.append(Column(pk, String(255), primary_key=True))

        table = Table(self.table_name, self.metadata, *columns)
        self.metadata.create_all(self.engine)
        self._table_initialized = True
        return table

    def _serialize_row(self, row: dict[str, Any]) -> dict[str, Any]:
        result = {}
        for k, v in row.items():
            if isinstance(v, (dict, list)):
                result[k] = json.dumps(v, default=str)
            else:
                result[k] = v
        return result

    def load(self, records: list[Record]) -> int:
        if not records:
            return 0

        if self.table is None:
            self.table = self._ensure_table(records[0].data)

        prepared_rows = [self._serialize_row(r.data) for r in records]

        is_sqlite = self.engine.dialect.name == "sqlite"

        with self.engine.begin() as conn:
            if self.mode == LoadMode.UPSERT and self.primary_keys and is_sqlite:
                for row in prepared_rows:
                    stmt = sqlite_upsert(self.table).values(row)
                    update_cols = {
                        k: v for k, v in row.items() if k not in self.primary_keys
                    }
                    if update_cols:
                        stmt = stmt.on_conflict_do_update(
                            index_elements=self.primary_keys,
                            set_=update_cols,
                        )
                    else:
                        stmt = stmt.on_conflict_do_nothing(
                            index_elements=self.primary_keys
                        )
                    conn.execute(stmt)
            else:
                conn.execute(self.table.insert(), prepared_rows)

        for r in records:
            r.mark_loaded()

        return len(records)

    def get_metadata(self) -> dict[str, Any]:
        return {
            "loader": "DatabaseLoader",
            "connection_url": self.connection_url,
            "table_name": self.table_name,
            "mode": self.mode.value,
            "primary_keys": self.primary_keys,
        }
