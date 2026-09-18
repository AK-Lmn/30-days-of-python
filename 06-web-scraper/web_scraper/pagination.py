from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlunparse
from bs4 import BeautifulSoup
from web_scraper.models import PaginationConfig


class PaginationHandler:
    def __init__(self) -> None:
        self.visited_urls: set[str] = set()

    def reset(self) -> None:
        self.visited_urls.clear()

    def mark_visited(self, url: str) -> None:
        self.visited_urls.add(url.strip())

    def has_visited(self, url: str) -> bool:
        return url.strip() in self.visited_urls

    def build_page_param_url(self, base_url: str, param_name: str, page_number: int) -> str:
        parsed = urlparse(base_url)
        query_dict = parse_qs(parsed.query)
        query_dict[param_name] = [str(page_number)]
        new_query = urlencode(query_dict, doseq=True)
        return urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment,
            )
        )

    def build_offset_url(
        self,
        base_url: str,
        offset_param: str,
        offset_value: int,
        limit_param: str | None = None,
        limit_value: int | None = None,
    ) -> str:
        parsed = urlparse(base_url)
        query_dict = parse_qs(parsed.query)
        query_dict[offset_param] = [str(offset_value)]
        if limit_param and limit_value is not None:
            query_dict[limit_param] = [str(limit_value)]
        new_query = urlencode(query_dict, doseq=True)
        return urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment,
            )
        )

    def extract_next_link_url(
        self,
        current_url: str,
        html: str,
        next_selector: str,
    ) -> str | None:
        soup = BeautifulSoup(html, "html.parser")
        next_element = soup.select_one(next_selector)
        if next_element is None:
            return None

        href = next_element.get("href")
        if not href or not isinstance(href, str):
            nested_a = next_element.find("a")
            if nested_a and isinstance(nested_a.get("href"), str):
                href = nested_a.get("href")
            else:
                return None

        absolute_url = urljoin(current_url, href)
        return absolute_url

    def get_next_url(
        self,
        current_url: str,
        page_index: int,
        html: str,
        config: PaginationConfig,
        current_item_count: int = 0,
    ) -> str | None:
        if config.max_pages is not None and (page_index + 1) >= config.max_pages:
            return None

        if config.max_items is not None and current_item_count >= config.max_items:
            return None

        candidate_url: str | None = None

        if config.strategy == "next_link":
            if not config.next_selector:
                return None
            candidate_url = self.extract_next_link_url(
                current_url,
                html,
                config.next_selector,
            )

        elif config.strategy == "page_param":
            next_page_num = config.start_page + (page_index + 1) * config.page_step
            candidate_url = self.build_page_param_url(
                current_url,
                config.page_param,
                next_page_num,
            )

        elif config.strategy == "offset":
            next_offset = config.start_offset + (page_index + 1) * config.offset_step
            candidate_url = self.build_offset_url(
                current_url,
                config.offset_param,
                next_offset,
                limit_param=config.limit_param,
                limit_value=config.offset_step,
            )

        if not candidate_url or candidate_url == current_url:
            return None

        if self.has_visited(candidate_url):
            return None

        return candidate_url
