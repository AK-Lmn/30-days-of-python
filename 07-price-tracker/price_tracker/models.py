from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Product:
    name: str
    url: str
    id: int | None = None
    selector: str = ""
    target_price: float | None = None
    current_price: float | None = None
    lowest_price: float | None = None
    highest_price: float | None = None
    currency: str = "USD"
    in_stock: bool = True
    tag: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_checked: str | None = None


@dataclass
class PriceRecord:
    product_id: int
    price: float
    id: int | None = None
    currency: str = "USD"
    in_stock: bool = True
    recorded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    note: str = ""


@dataclass
class PriceAlert:
    product_id: int
    product_name: str
    alert_type: str
    new_price: float
    id: int | None = None
    old_price: float | None = None
    target_price: float | None = None
    drop_amount: float = 0.0
    drop_percentage: float = 0.0
    currency: str = "USD"
    triggered_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    message: str = ""


@dataclass
class ScrapeResult:
    success: bool
    price: float | None = None
    currency: str = "USD"
    in_stock: bool = True
    title: str = ""
    error: str = ""


@dataclass
class ProductStats:
    product_id: int
    product_name: str
    current_price: float | None = None
    lowest_price: float | None = None
    highest_price: float | None = None
    average_price: float | None = None
    records_count: int = 0
    price_change_amount: float | None = None
    price_change_percentage: float | None = None
    history_prices: list[float] = field(default_factory=list)
