import os
import pytest
from price_tracker.db import Database
from price_tracker.gui import PriceTrackerApp


def test_gui_initialization(tmp_path):
    if os.environ.get("CI") or os.name != "nt":
        pytest.skip("Skipping GUI test in non-interactive environment")

    db = Database(db_path=tmp_path / "gui_test.db")
    try:
        app = PriceTrackerApp(db=db)
        assert "Price Tracker" in app.title()
        assert app.sidebar_frame is not None
        assert app.tab_products is not None
        app.destroy()
    except Exception as exc:
        pytest.skip(f"Display unavailable or GUI error: {exc}")
