from unittest.mock import MagicMock
from web_scraper.cache import ResponseCache
from web_scraper.client import HttpClient
from web_scraper.engine import ScraperEngine
from web_scraper.models import ItemRule, PageResponse, PaginationConfig, ScrapeJob
from web_scraper.rate_limiter import RateLimiter
from web_scraper.robots import RobotsChecker

PAGE1_HTML = (
    "<html><body>"
    "<div class='card'><span class='title'>Item 1</span><span class='price'>$10</span></div>"
    "<div class='card'><span class='title'>Item 2</span><span class='price'>$20</span></div>"
    "<a class='next' href='https://example.com/page/2'>Next</a>"
    "</body></html>"
)

PAGE2_HTML = (
    "<html><body>"
    "<div class='card'><span class='title'>Item 3</span><span class='price'>$30</span></div>"
    "<div class='card'><span class='title'>Item 4</span><span class='price'>$40</span></div>"
    "</body></html>"
)


def test_scraper_engine_multi_page(tmp_path):
    mock_client = MagicMock(spec=HttpClient)

    def fetch_side_effect(url, **kwargs):
        if "page/2" in url:
            return PageResponse(url=url, status_code=200, html=PAGE2_HTML)
        return PageResponse(url=url, status_code=200, html=PAGE1_HTML)

    mock_client.fetch.side_effect = fetch_side_effect

    mock_robots = MagicMock(spec=RobotsChecker)
    mock_robots.can_fetch.return_value = True

    cache = ResponseCache(cache_dir=tmp_path)
    engine = ScraperEngine(client=mock_client, robots_checker=mock_robots, cache=cache)

    job = ScrapeJob(
        url="https://example.com/page/1",
        container_selector="div.card",
        rules=[
            ItemRule(name="title", selector="span.title", extract="text"),
            ItemRule(name="price", selector="span.price", extract="text", regex=r"\d+", cast="int"),
        ],
        pagination=PaginationConfig(strategy="next_link", next_selector="a.next", max_pages=3),
        rate_limit_delay=0.0,
        rate_limit_jitter=0.0,
    )

    result = engine.run(job)

    assert result.total_pages == 2
    assert result.total_items == 4
    assert result.items[0]["title"] == "Item 1"
    assert result.items[0]["price"] == 10
    assert result.items[3]["title"] == "Item 4"
    assert result.items[3]["price"] == 40
    assert len(result.errors) == 0


def test_scraper_engine_max_items():
    mock_client = MagicMock(spec=HttpClient)
    mock_client.fetch.return_value = PageResponse(url="https://example.com", status_code=200, html=PAGE1_HTML)

    mock_robots = MagicMock(spec=RobotsChecker)
    mock_robots.can_fetch.return_value = True

    engine = ScraperEngine(client=mock_client, robots_checker=mock_robots)
    job = ScrapeJob(
        url="https://example.com",
        container_selector="div.card",
        rules=[ItemRule(name="title", selector="span.title", extract="text")],
        pagination=PaginationConfig(strategy="none", max_items=1),
        rate_limit_delay=0.0,
    )

    result = engine.run(job)
    assert result.total_items == 1
    assert result.items[0]["title"] == "Item 1"


def test_scraper_engine_robots_disallow():
    mock_robots = MagicMock(spec=RobotsChecker)
    mock_robots.can_fetch.return_value = False

    engine = ScraperEngine(robots_checker=mock_robots)
    job = ScrapeJob(url="https://secret.com/admin", respect_robots_txt=True)

    result = engine.run(job)
    assert result.total_items == 0
    assert len(result.errors) == 1
    assert "Disallowed by robots.txt" in result.errors[0]


def test_scraper_engine_cancellation():
    engine = ScraperEngine()
    engine.cancel()
    job = ScrapeJob(url="https://example.com")
    result = engine.run(job)
    assert result.total_pages == 0
