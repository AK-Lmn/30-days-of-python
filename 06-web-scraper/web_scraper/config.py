import os
from pathlib import Path

DEFAULT_TIMEOUT_SECONDS: float = 20.0
DEFAULT_MAX_RETRIES: int = 3
DEFAULT_BACKOFF_FACTOR: float = 1.5
DEFAULT_RATE_LIMIT_DELAY: float = 0.5
DEFAULT_RATE_LIMIT_JITTER: float = 0.2
DEFAULT_CACHE_DIR_NAME: str = ".cache"
DEFAULT_CACHE_TTL_SECONDS: int = 86400
DEFAULT_USER_AGENT: str = "WebScraperEngine/0.1.0 (+https://github.com/developer/30-days-of-python)"

DEFAULT_USER_AGENTS: list[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "WebScraperEngine/0.1.0 (+https://github.com/developer/30-days-of-python)",
]

SUPPORTED_EXPORTS: tuple[str, ...] = ("json", "jsonl", "csv", "md", "markdown", "sqlite", "db")


def get_base_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def get_cache_dir() -> Path:
    cache_path = os.getenv("SCRAPER_CACHE_DIR")
    if cache_path:
        path = Path(cache_path)
    else:
        path = get_base_dir() / DEFAULT_CACHE_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_output_dir() -> Path:
    output_path = os.getenv("SCRAPER_OUTPUT_DIR")
    if output_path:
        path = Path(output_path)
    else:
        path = get_base_dir() / "scraped_data"
    path.mkdir(parents=True, exist_ok=True)
    return path
