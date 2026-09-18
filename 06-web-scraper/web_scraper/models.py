from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class ItemRule:
    name: str
    selector: str
    extract: Literal["text", "html", "href", "src", "attr"] = "text"
    attr_name: str | None = None
    regex: str | None = None
    cast: Literal["str", "int", "float", "bool", "list"] = "str"
    default: Any = None
    strip: bool = True


@dataclass
class PaginationConfig:
    strategy: Literal["none", "next_link", "page_param", "offset"] = "none"
    next_selector: str | None = None
    page_param: str = "page"
    start_page: int = 1
    page_step: int = 1
    offset_param: str = "offset"
    limit_param: str = "limit"
    start_offset: int = 0
    offset_step: int = 20
    max_pages: int = 5
    max_items: int | None = None


@dataclass
class ScrapeJob:
    url: str
    container_selector: str | None = None
    rules: list[ItemRule] = field(default_factory=list)
    pagination: PaginationConfig = field(default_factory=PaginationConfig)
    headers: dict[str, str] = field(default_factory=dict)
    cookies: dict[str, str] = field(default_factory=dict)
    timeout: float = 20.0
    max_retries: int = 3
    backoff_factor: float = 1.5
    rate_limit_delay: float = 0.5
    rate_limit_jitter: float = 0.2
    respect_robots_txt: bool = True
    use_cache: bool = False
    cache_ttl_seconds: int = 86400
    user_agent: str | None = None


@dataclass
class PageResponse:
    url: str
    status_code: int
    html: str
    latency_ms: float = 0.0
    from_cache: bool = False
    error: str | None = None

    @property
    def is_success(self) -> bool:
        return 200 <= self.status_code < 300 and self.error is None


@dataclass
class ScrapeResult:
    job: ScrapeJob
    pages: list[PageResponse] = field(default_factory=list)
    items: list[dict[str, Any]] = field(default_factory=list)
    total_items: int = 0
    total_pages: int = 0
    duration_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)
