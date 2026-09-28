import time
from typing import Any
import httpx
from pipeforge.loaders.base import BaseLoader
from pipeforge.models.record import Record


class ApiLoader(BaseLoader):
    def __init__(
        self,
        endpoint_url: str,
        headers: dict[str, str] | None = None,
        auth_token: str | None = None,
        method: str = "POST",
        timeout_seconds: float = 10.0,
        max_retries: int = 3,
        backoff_seconds: float = 0.5,
    ):
        self.endpoint_url = endpoint_url
        self.headers = headers or {}
        if auth_token:
            self.headers["Authorization"] = f"Bearer {auth_token}"
        self.method = method.upper()
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds

    def load(self, records: list[Record]) -> int:
        if not records:
            return 0

        payload = [r.data for r in records]
        delay = self.backoff_seconds

        with httpx.Client() as client:
            last_err = None
            for attempt in range(self.max_retries):
                try:
                    if self.method == "POST":
                        res = client.post(
                            self.endpoint_url,
                            json=payload,
                            headers=self.headers,
                            timeout=self.timeout_seconds,
                        )
                    else:
                        res = client.put(
                            self.endpoint_url,
                            json=payload,
                            headers=self.headers,
                            timeout=self.timeout_seconds,
                        )
                    res.raise_for_status()
                    for r in records:
                        r.mark_loaded()
                    return len(records)
                except (httpx.RequestError, httpx.HTTPStatusError) as e:
                    last_err = e
                    if attempt == self.max_retries - 1:
                        raise
                    time.sleep(delay)
                    delay *= 2
            if last_err:
                raise last_err
        return 0

    def get_metadata(self) -> dict[str, Any]:
        return {
            "loader": "ApiLoader",
            "endpoint_url": self.endpoint_url,
            "method": self.method,
        }
