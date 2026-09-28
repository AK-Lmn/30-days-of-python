import time
from collections.abc import Generator
from typing import Any
import httpx
from pipeforge.extractors.base import BaseExtractor
from pipeforge.models.record import Record


class ApiExtractor(BaseExtractor):
    def __init__(
        self,
        endpoint_url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        auth_token: str | None = None,
        pagination_type: str = "none",
        page_param: str = "page",
        page_size_param: str = "per_page",
        page_size: int = 50,
        max_pages: int = 10,
        data_key: str | None = None,
        cursor_param: str = "cursor",
        next_cursor_key: str = "next_cursor",
        timeout_seconds: float = 10.0,
        max_retries: int = 3,
        backoff_seconds: float = 0.5,
    ):
        self.endpoint_url = endpoint_url
        self.params = params or {}
        self.headers = headers or {}
        if auth_token:
            self.headers["Authorization"] = f"Bearer {auth_token}"
        self.pagination_type = pagination_type.lower()
        self.page_param = page_param
        self.page_size_param = page_size_param
        self.page_size = page_size
        self.max_pages = max_pages
        self.data_key = data_key
        self.cursor_param = cursor_param
        self.next_cursor_key = next_cursor_key
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds

    def _fetch_page(self, client: httpx.Client, query_params: dict[str, Any]) -> dict[str, Any] | list[Any]:
        delay = self.backoff_seconds
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                response = client.get(
                    self.endpoint_url,
                    params=query_params,
                    headers=self.headers,
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                return response.json()
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                last_exception = e
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(delay)
                delay *= 2
        if last_exception:
            raise last_exception
        raise RuntimeError("Failed to fetch API response")

    def _extract_items(self, payload: Any) -> tuple[list[dict[str, Any]], str | None]:
        if isinstance(payload, list):
            return [x for x in payload if isinstance(x, dict)], None

        if not isinstance(payload, dict):
            return [], None

        next_cursor = None
        if self.next_cursor_key in payload:
            next_cursor = str(payload[self.next_cursor_key])

        if self.data_key and self.data_key in payload:
            raw_items = payload[self.data_key]
            items = [x for x in raw_items if isinstance(x, dict)] if isinstance(raw_items, list) else []
            return items, next_cursor

        for key in ["data", "items", "results", "records"]:
            if key in payload and isinstance(payload[key], list):
                return [x for x in payload[key] if isinstance(x, dict)], next_cursor

        return [payload], next_cursor

    def extract(self) -> Generator[Record, None, None]:
        row_number = 0
        with httpx.Client() as client:
            current_page = 1
            current_offset = 0
            current_cursor = None

            for page_idx in range(self.max_pages):
                query_params = self.params.copy()

                if self.pagination_type == "page":
                    query_params[self.page_param] = current_page
                    query_params[self.page_size_param] = self.page_size
                elif self.pagination_type == "offset":
                    query_params["offset"] = current_offset
                    query_params["limit"] = self.page_size
                elif self.pagination_type == "cursor" and current_cursor:
                    query_params[self.cursor_param] = current_cursor

                payload = self._fetch_page(client, query_params)
                items, next_cursor = self._extract_items(payload)

                if not items:
                    break

                for item in items:
                    row_number += 1
                    yield Record.from_raw(
                        raw=item,
                        row_number=row_number,
                        metadata={
                            "source": self.endpoint_url,
                            "page": current_page,
                            "format": "api",
                        },
                    )

                if self.pagination_type == "none":
                    break
                elif self.pagination_type == "page":
                    if len(items) < self.page_size:
                        break
                    current_page += 1
                elif self.pagination_type == "offset":
                    if len(items) < self.page_size:
                        break
                    current_offset += len(items)
                elif self.pagination_type == "cursor":
                    if not next_cursor or next_cursor == current_cursor:
                        break
                    current_cursor = next_cursor

    def get_metadata(self) -> dict[str, Any]:
        return {
            "extractor": "ApiExtractor",
            "endpoint_url": self.endpoint_url,
            "pagination_type": self.pagination_type,
        }
