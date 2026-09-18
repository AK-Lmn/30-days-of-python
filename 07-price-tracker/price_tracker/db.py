import sqlite3
from pathlib import Path
from price_tracker.config import get_db_path
from price_tracker.models import PriceAlert, PriceRecord, Product, ProductStats


class Database:
    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path) if db_path else get_db_path()
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_db(self) -> None:
        with self._get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL UNIQUE,
                    selector TEXT DEFAULT '',
                    target_price REAL,
                    current_price REAL,
                    lowest_price REAL,
                    highest_price REAL,
                    currency TEXT DEFAULT 'USD',
                    in_stock INTEGER DEFAULT 1,
                    tag TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_checked TEXT
                );

                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    price REAL NOT NULL,
                    currency TEXT DEFAULT 'USD',
                    in_stock INTEGER DEFAULT 1,
                    recorded_at TEXT NOT NULL,
                    note TEXT DEFAULT '',
                    FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    product_name TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    old_price REAL,
                    new_price REAL NOT NULL,
                    target_price REAL,
                    drop_amount REAL DEFAULT 0.0,
                    drop_percentage REAL DEFAULT 0.0,
                    currency TEXT DEFAULT 'USD',
                    triggered_at TEXT NOT NULL,
                    message TEXT NOT NULL,
                    FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_history_product ON price_history(product_id);
                CREATE INDEX IF NOT EXISTS idx_alerts_product ON alerts(product_id);
                """
            )

    def add_product(self, product: Product) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO products (
                    name, url, selector, target_price, current_price,
                    lowest_price, highest_price, currency, in_stock,
                    tag, created_at, updated_at, last_checked
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product.name,
                    product.url,
                    product.selector,
                    product.target_price,
                    product.current_price,
                    product.lowest_price,
                    product.highest_price,
                    product.currency,
                    1 if product.in_stock else 0,
                    product.tag,
                    product.created_at,
                    product.updated_at,
                    product.last_checked,
                ),
            )
            return cursor.lastrowid or 0

    def get_product(self, product_id: int) -> Product | None:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
            if not row:
                return None
            return self._row_to_product(row)

    def get_product_by_url(self, url: str) -> Product | None:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM products WHERE url = ?", (url,)).fetchone()
            if not row:
                return None
            return self._row_to_product(row)

    def list_products(self, tag: str | None = None, in_stock: bool | None = None) -> list[Product]:
        query = "SELECT * FROM products WHERE 1=1"
        params: list[object] = []

        if tag:
            query += " AND tag = ?"
            params.append(tag)
        if in_stock is not None:
            query += " AND in_stock = ?"
            params.append(1 if in_stock else 0)

        query += " ORDER BY id ASC"

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_product(r) for r in rows]

    def update_product(self, product: Product) -> bool:
        if product.id is None:
            return False
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE products SET
                    name = ?,
                    url = ?,
                    selector = ?,
                    target_price = ?,
                    current_price = ?,
                    lowest_price = ?,
                    highest_price = ?,
                    currency = ?,
                    in_stock = ?,
                    tag = ?,
                    updated_at = ?,
                    last_checked = ?
                WHERE id = ?
                """,
                (
                    product.name,
                    product.url,
                    product.selector,
                    product.target_price,
                    product.current_price,
                    product.lowest_price,
                    product.highest_price,
                    product.currency,
                    1 if product.in_stock else 0,
                    product.tag,
                    product.updated_at,
                    product.last_checked,
                    product.id,
                ),
            )
            return cursor.rowcount > 0

    def delete_product(self, product_id: int) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
            return cursor.rowcount > 0

    def add_price_record(self, record: PriceRecord) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO price_history (
                    product_id, price, currency, in_stock, recorded_at, note
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record.product_id,
                    record.price,
                    record.currency,
                    1 if record.in_stock else 0,
                    record.recorded_at,
                    record.note,
                ),
            )
            return cursor.lastrowid or 0

    def get_price_history(self, product_id: int, limit: int | None = None) -> list[PriceRecord]:
        query = "SELECT * FROM price_history WHERE product_id = ? ORDER BY recorded_at ASC"
        params: list[object] = [product_id]
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [
                PriceRecord(
                    id=row["id"],
                    product_id=row["product_id"],
                    price=row["price"],
                    currency=row["currency"],
                    in_stock=bool(row["in_stock"]),
                    recorded_at=row["recorded_at"],
                    note=row["note"],
                )
                for row in rows
            ]

    def add_alert(self, alert: PriceAlert) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO alerts (
                    product_id, product_name, alert_type, old_price,
                    new_price, target_price, drop_amount, drop_percentage,
                    currency, triggered_at, message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    alert.product_id,
                    alert.product_name,
                    alert.alert_type,
                    alert.old_price,
                    alert.new_price,
                    alert.target_price,
                    alert.drop_amount,
                    alert.drop_percentage,
                    alert.currency,
                    alert.triggered_at,
                    alert.message,
                ),
            )
            return cursor.lastrowid or 0

    def get_alerts(self, product_id: int | None = None, limit: int = 50) -> list[PriceAlert]:
        query = "SELECT * FROM alerts"
        params: list[object] = []
        if product_id is not None:
            query += " WHERE product_id = ?"
            params.append(product_id)
        query += " ORDER BY triggered_at DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [
                PriceAlert(
                    id=row["id"],
                    product_id=row["product_id"],
                    product_name=row["product_name"],
                    alert_type=row["alert_type"],
                    old_price=row["old_price"],
                    new_price=row["new_price"],
                    target_price=row["target_price"],
                    drop_amount=row["drop_amount"],
                    drop_percentage=row["drop_percentage"],
                    currency=row["currency"],
                    triggered_at=row["triggered_at"],
                    message=row["message"],
                )
                for row in rows
            ]

    def clear_alerts(self, product_id: int | None = None) -> int:
        with self._get_connection() as conn:
            if product_id is not None:
                cursor = conn.execute("DELETE FROM alerts WHERE product_id = ?", (product_id,))
            else:
                cursor = conn.execute("DELETE FROM alerts")
            return cursor.rowcount

    def get_product_stats(self, product_id: int) -> ProductStats | None:
        product = self.get_product(product_id)
        if not product:
            return None

        records = self.get_price_history(product_id)
        prices = [r.price for r in records]

        if not prices:
            return ProductStats(
                product_id=product_id,
                product_name=product.name,
                current_price=product.current_price,
                lowest_price=product.lowest_price,
                highest_price=product.highest_price,
            )

        lowest = min(prices)
        highest = max(prices)
        avg_price = round(sum(prices) / len(prices), 2)
        change_amount = None
        change_pct = None

        if len(prices) >= 2:
            change_amount = round(prices[-1] - prices[0], 2)
            if prices[0] > 0:
                change_pct = round(((prices[-1] - prices[0]) / prices[0]) * 100, 2)

        return ProductStats(
            product_id=product_id,
            product_name=product.name,
            current_price=prices[-1],
            lowest_price=lowest,
            highest_price=highest,
            average_price=avg_price,
            records_count=len(prices),
            price_change_amount=change_amount,
            price_change_percentage=change_pct,
            history_prices=prices,
        )

    def _row_to_product(self, row: sqlite3.Row) -> Product:
        return Product(
            id=row["id"],
            name=row["name"],
            url=row["url"],
            selector=row["selector"] or "",
            target_price=row["target_price"],
            current_price=row["current_price"],
            lowest_price=row["lowest_price"],
            highest_price=row["highest_price"],
            currency=row["currency"] or "USD",
            in_stock=bool(row["in_stock"]),
            tag=row["tag"] or "",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            last_checked=row["last_checked"],
        )
