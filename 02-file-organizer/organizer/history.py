import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from organizer.models import OrganizeAction


class HistoryManager:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    source_directory TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    action_count INTEGER NOT NULL,
                    undone INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    source_path TEXT NOT NULL,
                    destination_path TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    category TEXT NOT NULL,
                    size INTEGER NOT NULL,
                    checksum TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                )
                """
            )
            conn.commit()

    def record_session(
        self,
        source_dir: Path,
        strategy: str,
        actions: list[OrganizeAction],
    ) -> int:
        executable_actions = [a for a in actions if a.action_type in ("move", "copy")]
        if not executable_actions:
            return 0

        now_str = datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO sessions (timestamp, source_directory, strategy, action_count, undone)
                VALUES (?, ?, ?, ?, 0)
                """,
                (now_str, str(source_dir.resolve()), strategy, len(executable_actions)),
            )
            session_id = cursor.lastrowid

            cursor.executemany(
                """
                INSERT INTO actions (session_id, source_path, destination_path, action_type, category, size, checksum)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        session_id,
                        str(act.source_path.resolve()),
                        str(act.destination_path.resolve()),
                        act.action_type,
                        act.category,
                        act.size,
                        act.checksum,
                    )
                    for act in executable_actions
                ],
            )
            conn.commit()
            return int(session_id or 0)

    def get_last_active_session(self) -> Optional[tuple[int, list[OrganizeAction]]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id FROM sessions
                WHERE undone = 0
                ORDER BY id DESC
                LIMIT 1
                """
            )
            row = cursor.fetchone()
            if not row:
                return None
            session_id = int(row["id"])
            return self.get_session_by_id(session_id)

    def get_session_by_id(self, session_id: int) -> Optional[tuple[int, list[OrganizeAction]]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, undone FROM sessions WHERE id = ?",
                (session_id,),
            )
            sess_row = cursor.fetchone()
            if not sess_row:
                return None

            cursor.execute(
                """
                SELECT source_path, destination_path, action_type, category, size, checksum
                FROM actions
                WHERE session_id = ?
                ORDER BY id DESC
                """,
                (session_id,),
            )
            actions = [
                OrganizeAction(
                    source_path=Path(r["source_path"]),
                    destination_path=Path(r["destination_path"]),
                    action_type=r["action_type"],
                    category=r["category"],
                    size=r["size"],
                    checksum=r["checksum"],
                )
                for r in cursor.fetchall()
            ]
            return session_id, actions

    def mark_session_undone(self, session_id: int) -> None:
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE sessions SET undone = 1 WHERE id = ?",
                (session_id,),
            )
            conn.commit()

    def list_sessions(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, timestamp, source_directory, strategy, action_count, undone
                FROM sessions
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]
