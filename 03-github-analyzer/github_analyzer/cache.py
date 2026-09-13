import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional


class ResponseCache:
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            self.db_path = Path(".analyzer_cache.db")
        else:
            self.db_path = Path(db_path)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_entries (
                    cache_key TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    expires_at REAL NOT NULL
                )
                """
            )
            conn.commit()

    def get(self, key: str) -> Optional[Any]:
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT payload, expires_at FROM cache_entries WHERE cache_key = ?",
                (key,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            payload_str, expires_at = row
            if now > expires_at:
                self.delete(key)
                return None
            return json.loads(payload_str)

    def set(self, key: str, data: Any, ttl_seconds: int = 3600) -> None:
        expires_at = time.time() + ttl_seconds
        payload_str = json.dumps(data)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO cache_entries (cache_key, payload, expires_at)
                VALUES (?, ?, ?)
                """,
                (key, payload_str, expires_at),
            )
            conn.commit()

    def delete(self, key: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cache_entries WHERE cache_key = ?", (key,))
            conn.commit()
            return cursor.rowcount > 0

    def clear(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cache_entries")
            conn.commit()
            return cursor.rowcount

    def prune_expired(self) -> int:
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM cache_entries WHERE expires_at < ?", (now,))
            conn.commit()
            return cursor.rowcount
