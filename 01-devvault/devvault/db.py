import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from devvault.models import VaultItem


class Database:

    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    item_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    language TEXT,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            conn.execute("CREATE INDEX IF NOT EXISTS idx_items_type ON items(item_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_items_created ON items(created_at)")

            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(
                    title,
                    content,
                    description,
                    content='items',
                    content_rowid='id'
                )
            """)

            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS items_ai AFTER INSERT ON items BEGIN
                    INSERT INTO items_fts(rowid, title, content, description)
                    VALUES (new.id, new.title, new.content, coalesce(new.description, ''));
                END;
            """)

            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS items_ad AFTER DELETE ON items BEGIN
                    INSERT INTO items_fts(items_fts, rowid, title, content, description)
                    VALUES ('delete', old.id, old.title, old.content, coalesce(old.description, ''));
                END;
            """)

            conn.execute("""
                CREATE TRIGGER IF NOT EXISTS items_au AFTER UPDATE ON items BEGIN
                    INSERT INTO items_fts(items_fts, rowid, title, content, description)
                    VALUES ('delete', old.id, old.title, old.content, coalesce(old.description, ''));
                    INSERT INTO items_fts(rowid, title, content, description)
                    VALUES (new.id, new.title, new.content, coalesce(new.description, ''));
                END;
            """)

    def add_item(self, item: VaultItem) -> VaultItem:
        now = datetime.now().isoformat(timespec="seconds")
        item.created_at = now
        item.updated_at = now

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO items (title, item_type, content, language, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.title,
                    item.item_type,
                    item.content,
                    item.language,
                    item.description,
                    item.created_at,
                    item.updated_at,
                ),
            )
            item.id = cursor.lastrowid

        return item

    def get_item(self, item_id: int) -> Optional[VaultItem]:
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return VaultItem.from_row(row)

    def list_items(
        self,
        item_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[VaultItem]:
        query = "SELECT * FROM items WHERE 1=1"
        params: List[Any] = []

        if item_type:
            query += " AND item_type = ?"
            params.append(item_type.strip().lower())

        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            return [VaultItem.from_row(r) for r in cursor.fetchall()]

    def search_items(
        self,
        search_query: str,
        item_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[VaultItem]:
        cleaned_query = search_query.strip()
        if not cleaned_query:
            return self.list_items(item_type=item_type, limit=limit)

        words = [w for w in cleaned_query.replace('"', ' ').replace("'", " ").split() if w]
        fts_match_expr = " ".join(f'"{w}"*' for w in words) if words else f'"{cleaned_query}"'

        results: List[VaultItem] = []
        try:
            with self._get_connection() as conn:
                sql = """
                    SELECT items.*
                    FROM items_fts
                    JOIN items ON items.id = items_fts.rowid
                    WHERE items_fts MATCH ?
                """
                params: List[Any] = [fts_match_expr]

                if item_type:
                    sql += " AND items.item_type = ?"
                    params.append(item_type.strip().lower())

                sql += " ORDER BY rank LIMIT ?"
                params.append(limit)

                cursor = conn.execute(sql, params)
                results = [VaultItem.from_row(r) for r in cursor.fetchall()]
        except sqlite3.OperationalError:
            results = self._fallback_like_search(cleaned_query, item_type=item_type, limit=limit)

        return results

    def _fallback_like_search(
        self,
        query: str,
        item_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[VaultItem]:
        with self._get_connection() as conn:
            sql = """
                SELECT * FROM items
                WHERE (title LIKE ? OR content LIKE ? OR description LIKE ?)
            """
            pattern = f"%{query}%"
            params: List[Any] = [pattern, pattern, pattern]

            if item_type:
                sql += " AND item_type = ?"
                params.append(item_type.strip().lower())

            sql += " ORDER BY id DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(sql, params)
            return [VaultItem.from_row(r) for r in cursor.fetchall()]

    def update_item(self, item_id: int, **fields: Any) -> Optional[VaultItem]:
        current = self.get_item(item_id)
        if not current:
            return None

        allowed_fields = {
            "title",
            "item_type",
            "content",
            "language",
            "description",
        }
        updates: List[str] = []
        params: List[Any] = []

        for key, value in fields.items():
            if key in allowed_fields and value is not None:
                if key == "item_type":
                    value = str(value).strip().lower()
                updates.append(f"{key} = ?")
                params.append(value)

        if not updates:
            return current

        now = datetime.now().isoformat(timespec="seconds")
        updates.append("updated_at = ?")
        params.append(now)

        params.append(item_id)
        sql = f"UPDATE items SET {', '.join(updates)} WHERE id = ?"

        with self._get_connection() as conn:
            conn.execute(sql, params)

        return self.get_item(item_id)

    def delete_item(self, item_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
            return cursor.rowcount > 0

    def get_vault_stats(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            total_items = conn.execute("SELECT count(*) FROM items").fetchone()[0]

            cursor = conn.execute("SELECT item_type, count(*) FROM items GROUP BY item_type")
            by_type = {row[0]: row[1] for row in cursor.fetchall()}

            recent = conn.execute("SELECT max(updated_at) FROM items").fetchone()[0]

        return {
            "total_items": total_items,
            "by_type": by_type,
            "last_updated": recent or "Never",
            "db_path": str(self.db_path),
        }

    def export_all(self, format_type: str = "json") -> str:
        items = self.list_items(limit=10000)
        if format_type.lower() == "markdown":
            md_lines = ["# DevVault Export\n"]
            for item in items:
                md_lines.append(f"## [{item.id}] {item.title} ({item.item_type})")
                if item.description:
                    md_lines.append(f"*{item.description}*\n")
                if item.item_type == "snippet":
                    lang = item.language or ""
                    md_lines.append(f"```{lang}\n{item.content}\n```\n")
                elif item.item_type == "command":
                    md_lines.append(f"```bash\n{item.content}\n```\n")
                elif item.item_type == "url":
                    md_lines.append(f"[Open Link]({item.content})\n")
                else:
                    md_lines.append(f"{item.content}\n")
                md_lines.append("---\n")
            return "\n".join(md_lines)

        return json.dumps([item.to_dict() for item in items], indent=2)

    def import_all(self, data: List[Dict[str, Any]]) -> int:
        count = 0
        for entry in data:
            if not isinstance(entry, dict):
                continue
            title = entry.get("title")
            content = entry.get("content")
            item_type = entry.get("item_type", "note")
            if not title or not content:
                continue
            try:
                item = VaultItem(
                    title=title,
                    item_type=item_type,
                    content=content,
                    language=entry.get("language"),
                    description=entry.get("description"),
                )
                self.add_item(item)
                count += 1
            except Exception:
                continue
        return count
