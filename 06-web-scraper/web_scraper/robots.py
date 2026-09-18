from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import httpx


class RobotsChecker:
    def __init__(self) -> None:
        self.parsers: dict[str, RobotFileParser] = {}
        self.crawl_delays: dict[str, float | None] = {}

    def get_origin(self, url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def load_robots_txt(
        self,
        url: str,
        user_agent: str,
        client: httpx.Client | None = None,
        timeout: float = 10.0,
    ) -> RobotFileParser:
        origin = self.get_origin(url)
        if origin in self.parsers:
            return self.parsers[origin]

        robots_url = f"{origin}/robots.txt"
        parser = RobotFileParser()
        parser.set_url(robots_url)

        try:
            if client is not None:
                response = client.get(
                    robots_url,
                    headers={"User-Agent": user_agent},
                    timeout=timeout,
                )
                status_code = response.status_code
                content_text = response.text
            else:
                with httpx.Client(timeout=timeout) as temp_client:
                    response = temp_client.get(
                        robots_url,
                        headers={"User-Agent": user_agent},
                    )
                    status_code = response.status_code
                    content_text = response.text

            if status_code in (200, 203):
                parser.parse(content_text.splitlines())
            elif status_code in (401, 403):
                parser.disallow_all = True
            elif status_code >= 400:
                parser.allow_all = True
            else:
                parser.allow_all = True
        except Exception:
            parser.allow_all = True

        self.parsers[origin] = parser
        try:
            self.crawl_delays[origin] = parser.crawl_delay(user_agent)
        except Exception:
            self.crawl_delays[origin] = None

        return parser

    def can_fetch(
        self,
        url: str,
        user_agent: str,
        client: httpx.Client | None = None,
        timeout: float = 10.0,
    ) -> bool:
        parser = self.load_robots_txt(url, user_agent, client, timeout)
        return parser.can_fetch(user_agent, url)

    def get_crawl_delay(self, url: str, user_agent: str) -> float | None:
        origin = self.get_origin(url)
        if origin not in self.crawl_delays:
            self.load_robots_txt(url, user_agent)
        return self.crawl_delays.get(origin)

    def clear(self) -> None:
        self.parsers.clear()
        self.crawl_delays.clear()
