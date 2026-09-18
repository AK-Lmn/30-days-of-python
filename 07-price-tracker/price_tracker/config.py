import os
from pathlib import Path

DEFAULT_TIMEOUT_SECONDS: float = 15.0
DEFAULT_USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 PriceTracker/0.1.0"
DEFAULT_DB_NAME: str = "price_tracker.db"
DEFAULT_EXPORT_DIR_NAME: str = "exports"
DEFAULT_CHECK_INTERVAL_SECONDS: int = 3600
DEFAULT_DROP_PERCENTAGE_ALERT: float = 5.0

CURRENCY_SYMBOLS: dict[str, str] = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
    "₹": "INR",
    "C$": "CAD",
    "A$": "AUD",
    "CHF": "CHF",
}


def get_base_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def get_db_path() -> Path:
    custom_path = os.getenv("PRICE_TRACKER_DB")
    if custom_path:
        path = Path(custom_path)
    else:
        path = get_base_dir() / DEFAULT_DB_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_export_dir() -> Path:
    custom_path = os.getenv("PRICE_TRACKER_EXPORT_DIR")
    if custom_path:
        path = Path(custom_path)
    else:
        path = get_base_dir() / DEFAULT_EXPORT_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path
