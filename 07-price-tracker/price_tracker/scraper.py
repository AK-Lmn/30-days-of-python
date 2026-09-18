import httpx
from price_tracker.config import DEFAULT_TIMEOUT_SECONDS, DEFAULT_USER_AGENT


class WebScraper:
    def __init__(self, timeout: float = DEFAULT_TIMEOUT_SECONDS, user_agent: str = DEFAULT_USER_AGENT):
        self.timeout = timeout
        self.headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "DNT": "1",
        }

    def fetch_html(self, url: str) -> tuple[str, str | None]:
        try:
            with httpx.Client(timeout=self.timeout, headers=self.headers, follow_redirects=True) as client:
                response = client.get(url)
                response.raise_for_status()
                return response.text, None
        except httpx.HTTPStatusError as exc:
            return "", f"HTTP error {exc.response.status_code}"
        except httpx.RequestError as exc:
            return "", f"Network error: {str(exc)}"
        except Exception as exc:
            return "", f"Unexpected error: {str(exc)}"
