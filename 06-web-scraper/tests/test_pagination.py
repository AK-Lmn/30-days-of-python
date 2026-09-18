from web_scraper.models import PaginationConfig
from web_scraper.pagination import PaginationHandler


def test_pagination_next_link():
    html_page1 = (
        "<html><body>"
        "<ul class='pager'>"
        "<li class='next'><a href='/catalogue/page-2.html'>Next</a></li>"
        "</ul>"
        "</body></html>"
    )
    handler = PaginationHandler()
    config = PaginationConfig(strategy="next_link", next_selector="li.next > a", max_pages=3)

    next_url = handler.get_next_url(
        "https://books.toscrape.com/catalogue/page-1.html",
        page_index=0,
        html=html_page1,
        config=config,
    )
    assert next_url == "https://books.toscrape.com/catalogue/page-2.html"


def test_pagination_page_param():
    handler = PaginationHandler()
    config = PaginationConfig(strategy="page_param", page_param="p", start_page=1, page_step=1, max_pages=4)

    next_url = handler.get_next_url(
        "https://example.com/items?sort=asc",
        page_index=0,
        html="<html></html>",
        config=config,
    )
    assert "p=2" in next_url
    assert "sort=asc" in next_url


def test_pagination_offset():
    handler = PaginationHandler()
    config = PaginationConfig(strategy="offset", offset_param="offset", start_offset=0, offset_step=25, max_pages=5)

    next_url = handler.get_next_url(
        "https://example.com/api/items",
        page_index=0,
        html="<html></html>",
        config=config,
    )
    assert "offset=25" in next_url


def test_pagination_stops_at_max_pages():
    handler = PaginationHandler()
    config = PaginationConfig(strategy="page_param", page_param="page", max_pages=2)

    next_url = handler.get_next_url(
        "https://example.com/items?page=2",
        page_index=1,
        html="<html></html>",
        config=config,
    )
    assert next_url is None


def test_pagination_stops_at_max_items():
    handler = PaginationHandler()
    config = PaginationConfig(strategy="page_param", page_param="page", max_items=20)

    next_url = handler.get_next_url(
        "https://example.com/items?page=1",
        page_index=0,
        html="<html></html>",
        config=config,
        current_item_count=20,
    )
    assert next_url is None


def test_pagination_detects_visited_loop():
    handler = PaginationHandler()
    config = PaginationConfig(strategy="next_link", next_selector="a.next")
    html = '<html><a class="next" href="/items?page=1">Next</a></html>'

    handler.mark_visited("https://example.com/items?page=1")
    next_url = handler.get_next_url(
        "https://example.com/items?page=1",
        page_index=0,
        html=html,
        config=config,
    )
    assert next_url is None
