import json
from pathlib import Path
import sqlite3
from typing import List, Optional
from api_cli.config import get_database_path
from api_cli.models import Environment, HistoryEntry, SavedRequest


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = db_path or get_database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[Path] = None) -> None:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS environments (
                name TEXT PRIMARY KEY,
                base_url TEXT NOT NULL DEFAULT '',
                headers TEXT NOT NULL DEFAULT '{}',
                variables TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS saved_requests (
                name TEXT PRIMARY KEY,
                method TEXT NOT NULL,
                url TEXT NOT NULL,
                headers TEXT NOT NULL DEFAULT '{}',
                query_params TEXT NOT NULL DEFAULT '{}',
                body TEXT,
                env_name TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                method TEXT NOT NULL,
                url TEXT NOT NULL,
                status_code INTEGER NOT NULL,
                latency_ms REAL NOT NULL,
                request_headers TEXT NOT NULL DEFAULT '{}',
                request_body TEXT,
                response_headers TEXT NOT NULL DEFAULT '{}',
                response_body TEXT NOT NULL DEFAULT '',
                size_bytes INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.commit()


def save_environment(env: Environment, db_path: Optional[Path] = None) -> None:
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO environments (name, base_url, headers, variables, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                base_url=excluded.base_url,
                headers=excluded.headers,
                variables=excluded.variables,
                updated_at=excluded.updated_at
            """,
            (
                env.name,
                env.base_url,
                json.dumps(env.headers),
                json.dumps(env.variables),
                env.updated_at,
            ),
        )
        conn.commit()


def get_environment(name: str, db_path: Optional[Path] = None) -> Optional[Environment]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, base_url, headers, variables, updated_at FROM environments WHERE name = ?",
            (name,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return Environment(
            name=row["name"],
            base_url=row["base_url"],
            headers=json.loads(row["headers"]),
            variables=json.loads(row["variables"]),
            updated_at=row["updated_at"],
        )


def list_environments(db_path: Optional[Path] = None) -> List[Environment]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, base_url, headers, variables, updated_at FROM environments ORDER BY name ASC")
        rows = cursor.fetchall()
        return [
            Environment(
                name=row["name"],
                base_url=row["base_url"],
                headers=json.loads(row["headers"]),
                variables=json.loads(row["variables"]),
                updated_at=row["updated_at"],
            )
            for row in rows
        ]


def delete_environment(name: str, db_path: Optional[Path] = None) -> bool:
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM environments WHERE name = ?", (name,))
        deleted = cursor.rowcount > 0
        if deleted:
            cursor.execute("SELECT value FROM settings WHERE key = 'active_environment'")
            row = cursor.fetchone()
            if row and row["value"] == name:
                cursor.execute("DELETE FROM settings WHERE key = 'active_environment'")
        conn.commit()
        return deleted


def set_active_environment(name: Optional[str], db_path: Optional[Path] = None) -> None:
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        if name is None or name == "":
            cursor.execute("DELETE FROM settings WHERE key = 'active_environment'")
        else:
            cursor.execute(
                """
                INSERT INTO settings (key, value) VALUES ('active_environment', ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (name,),
            )
        conn.commit()


def get_active_environment(db_path: Optional[Path] = None) -> Optional[str]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'active_environment'")
        row = cursor.fetchone()
        if not row:
            return None
        return row["value"]


def save_request(req: SavedRequest, db_path: Optional[Path] = None) -> None:
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO saved_requests (name, method, url, headers, query_params, body, env_name, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                method=excluded.method,
                url=excluded.url,
                headers=excluded.headers,
                query_params=excluded.query_params,
                body=excluded.body,
                env_name=excluded.env_name,
                created_at=excluded.created_at
            """,
            (
                req.name,
                req.method.upper(),
                req.url,
                json.dumps(req.headers),
                json.dumps(req.query_params),
                req.body,
                req.env_name,
                req.created_at,
            ),
        )
        conn.commit()


def get_saved_request(name: str, db_path: Optional[Path] = None) -> Optional[SavedRequest]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, method, url, headers, query_params, body, env_name, created_at FROM saved_requests WHERE name = ?",
            (name,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return SavedRequest(
            name=row["name"],
            method=row["method"],
            url=row["url"],
            headers=json.loads(row["headers"]),
            query_params=json.loads(row["query_params"]),
            body=row["body"],
            env_name=row["env_name"],
            created_at=row["created_at"],
        )


def list_saved_requests(db_path: Optional[Path] = None) -> List[SavedRequest]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, method, url, headers, query_params, body, env_name, created_at FROM saved_requests ORDER BY name ASC"
        )
        rows = cursor.fetchall()
        return [
            SavedRequest(
                name=row["name"],
                method=row["method"],
                url=row["url"],
                headers=json.loads(row["headers"]),
                query_params=json.loads(row["query_params"]),
                body=row["body"],
                env_name=row["env_name"],
                created_at=row["created_at"],
            )
            for row in rows
        ]


def delete_saved_request(name: str, db_path: Optional[Path] = None) -> bool:
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM saved_requests WHERE name = ?", (name,))
        conn.commit()
        return cursor.rowcount > 0


def add_history_entry(entry: HistoryEntry, db_path: Optional[Path] = None) -> int:
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO history (timestamp, method, url, status_code, latency_ms, request_headers, request_body, response_headers, response_body, size_bytes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.timestamp,
                entry.method.upper(),
                entry.url,
                entry.status_code,
                entry.latency_ms,
                json.dumps(entry.request_headers),
                entry.request_body,
                json.dumps(entry.response_headers),
                entry.response_body,
                entry.size_bytes,
            ),
        )
        conn.commit()
        return cursor.lastrowid or 0


def list_history(limit: int = 50, db_path: Optional[Path] = None) -> List[HistoryEntry]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, timestamp, method, url, status_code, latency_ms, request_headers, request_body, response_headers, response_body, size_bytes
            FROM history
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        return [
            HistoryEntry(
                id=row["id"],
                timestamp=row["timestamp"],
                method=row["method"],
                url=row["url"],
                status_code=row["status_code"],
                latency_ms=row["latency_ms"],
                request_headers=json.loads(row["request_headers"]),
                request_body=row["request_body"],
                response_headers=json.loads(row["response_headers"]),
                response_body=row["response_body"],
                size_bytes=row["size_bytes"],
            )
            for row in rows
        ]


def get_history_entry(entry_id: int, db_path: Optional[Path] = None) -> Optional[HistoryEntry]:
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, timestamp, method, url, status_code, latency_ms, request_headers, request_body, response_headers, response_body, size_bytes
            FROM history
            WHERE id = ?
            """,
            (entry_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return HistoryEntry(
            id=row["id"],
            timestamp=row["timestamp"],
            method=row["method"],
            url=row["url"],
            status_code=row["status_code"],
            latency_ms=row["latency_ms"],
            request_headers=json.loads(row["request_headers"]),
            request_body=row["request_body"],
            response_headers=json.loads(row["response_headers"]),
            response_body=row["response_body"],
            size_bytes=row["size_bytes"],
        )


def clear_history(db_path: Optional[Path] = None) -> int:
    init_db(db_path)
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM history")
        count = cursor.rowcount
        conn.commit()
        return count
