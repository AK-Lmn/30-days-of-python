from collections.abc import Callable
import time
from web_scraper.cache import ResponseCache
from web_scraper.client import HttpClient
from web_scraper.models import PageResponse, ScrapeJob, ScrapeResult
from web_scraper.pagination import PaginationHandler
from web_scraper.parser import HtmlParser
from web_scraper.rate_limiter import RateLimiter
from web_scraper.robots import RobotsChecker


class ScraperEngine:
    def __init__(
        self,
        client: HttpClient | None = None,
        rate_limiter: RateLimiter | None = None,
        robots_checker: RobotsChecker | None = None,
        cache: ResponseCache | None = None,
        parser: HtmlParser | None = None,
        pagination_handler: PaginationHandler | None = None,
    ) -> None:
        self.client = client or HttpClient()
        self.rate_limiter = rate_limiter or RateLimiter()
        self.robots_checker = robots_checker or RobotsChecker()
        self.cache = cache or ResponseCache()
        self.parser = parser or HtmlParser()
        self.pagination_handler = pagination_handler or PaginationHandler()
        self._is_cancelled: bool = False

    def cancel(self) -> None:
        self._is_cancelled = True

    def reset_cancellation(self) -> None:
        self._is_cancelled = False

    def run(
        self,
        job: ScrapeJob,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> ScrapeResult:
        self.pagination_handler.reset()
        start_time = time.perf_counter()

        result = ScrapeResult(job=job)
        current_url: str | None = job.url
        page_index = 0

        while current_url and not self._is_cancelled:
            if job.pagination.max_pages is not None and page_index >= job.pagination.max_pages:
                break

            if job.pagination.max_items is not None and len(result.items) >= job.pagination.max_items:
                break

            self.pagination_handler.mark_visited(current_url)

            if job.respect_robots_txt:
                allowed = self.robots_checker.can_fetch(
                    current_url,
                    job.user_agent or "WebScraperEngine",
                )
                if not allowed:
                    msg = f"Skipping {current_url}: Disallowed by robots.txt"
                    result.errors.append(msg)
                    break

            page_resp: PageResponse | None = None

            if job.use_cache:
                page_resp = self.cache.get(current_url, job.cache_ttl_seconds)

            if page_resp is None:
                if page_index > 0 or job.rate_limit_delay > 0:
                    self.rate_limiter.wait(
                        current_url,
                        job.rate_limit_delay,
                        job.rate_limit_jitter,
                    )

                page_resp = self.client.fetch(
                    url=current_url,
                    headers=job.headers,
                    cookies=job.cookies,
                    timeout=job.timeout,
                    max_retries=job.max_retries,
                    backoff_factor=job.backoff_factor,
                    user_agent=job.user_agent,
                )

                if job.use_cache and page_resp.is_success:
                    self.cache.set(current_url, page_resp)

            result.pages.append(page_resp)

            if not page_resp.is_success:
                err = page_resp.error or f"Failed to fetch {current_url} (HTTP {page_resp.status_code})"
                result.errors.append(err)
                break

            new_items: list[dict] = []
            if job.container_selector:
                new_items = self.parser.extract_collection(
                    page_resp.html,
                    job.container_selector,
                    job.rules,
                )
            elif job.rules:
                single_item = self.parser.extract_single(page_resp.html, job.rules)
                new_items = [single_item]

            if job.pagination.max_items is not None:
                remaining_quota = job.pagination.max_items - len(result.items)
                new_items = new_items[:remaining_quota]

            result.items.extend(new_items)

            page_index += 1

            if progress_callback:
                progress_callback(page_index, len(result.items), current_url)

            if job.pagination.max_items is not None and len(result.items) >= job.pagination.max_items:
                break

            current_url = self.pagination_handler.get_next_url(
                current_url,
                page_index - 1,
                page_resp.html,
                job.pagination,
                current_item_count=len(result.items),
            )

        result.total_items = len(result.items)
        result.total_pages = len(result.pages)
        result.duration_seconds = round(time.perf_counter() - start_time, 3)

        return result
