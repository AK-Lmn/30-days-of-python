import hashlib
import json
from pathlib import Path
import time
from web_scraper.config import get_cache_dir
from web_scraper.models import PageResponse


class ResponseCache:
    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or get_cache_dir()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def generate_cache_key(self, url: str) -> str:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    def get_cache_file_path(self, url: str) -> Path:
        key = self.generate_cache_key(url)
        return self.cache_dir / f"{key}.json"

    def get(self, url: str, max_age_seconds: int = 86400) -> PageResponse | None:
        cache_file = self.get_cache_file_path(url)
        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "r", encoding="utf-8") as file:
                data = json.load(file)

            created_at = data.get("timestamp", 0)
            if (time.time() - created_at) > max_age_seconds:
                cache_file.unlink(missing_ok=True)
                return None

            return PageResponse(
                url=data["url"],
                status_code=data["status_code"],
                html=data["html"],
                latency_ms=data.get("latency_ms", 0.0),
                from_cache=True,
            )
        except Exception:
            return None

    def set(self, url: str, page: PageResponse) -> None:
        if not page.is_success:
            return

        cache_file = self.get_cache_file_path(url)
        payload = {
            "url": page.url,
            "status_code": page.status_code,
            "html": page.html,
            "latency_ms": page.latency_ms,
            "timestamp": time.time(),
        }

        try:
            with open(cache_file, "w", encoding="utf-8") as file:
                json.dump(payload, file, ensure_ascii=False)
        except Exception:
            pass

    def clear(self) -> int:
        removed_count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                removed_count += 1
            except Exception:
                pass
        return removed_count

    def count(self) -> int:
        return len(list(self.cache_dir.glob("*.json")))
