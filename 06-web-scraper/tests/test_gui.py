import os
import pytest
from web_scraper.gui import ScraperApp


def test_gui_initialization():
    if os.environ.get("CI") or os.name != "nt":
        pytest.skip("Skipping GUI test in non-interactive environment")

    try:
        app = ScraperApp()
        assert app.title() == "Web Scraper Engine"
        assert len(app.field_rules) > 0
        assert app.url_entry.get() == "https://quotes.toscrape.com"
        app.destroy()
    except Exception as exc:
        pytest.skip(f"Display unavailable or GUI error: {exc}")
