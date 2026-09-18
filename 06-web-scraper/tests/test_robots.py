from unittest.mock import MagicMock
import httpx
from web_scraper.robots import RobotsChecker


def test_robots_allowed():
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.text = "User-agent: *\nDisallow: /private/\nAllow: /public/\nCrawl-delay: 2\n"

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_resp

    checker = RobotsChecker()
    assert checker.can_fetch("https://example.com/public/data", "MyBot", client=mock_client) is True
    assert checker.can_fetch("https://example.com/private/data", "MyBot", client=mock_client) is False
    assert checker.get_crawl_delay("https://example.com", "MyBot") == 2.0


def test_robots_disallowed_all_on_403():
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 403
    mock_resp.text = ""

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_resp

    checker = RobotsChecker()
    assert checker.can_fetch("https://example.com/anypage", "MyBot", client=mock_client) is False


def test_robots_allowed_all_on_404():
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 404
    mock_resp.text = ""

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_resp

    checker = RobotsChecker()
    assert checker.can_fetch("https://example.com/anypage", "MyBot", client=mock_client) is True


def test_robots_clear():
    checker = RobotsChecker()
    checker.parsers["https://example.com"] = MagicMock()
    checker.crawl_delays["https://example.com"] = 5.0
    checker.clear()
    assert len(checker.parsers) == 0
    assert len(checker.crawl_delays) == 0
