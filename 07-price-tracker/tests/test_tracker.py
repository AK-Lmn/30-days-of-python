from unittest.mock import MagicMock
from price_tracker.db import Database
from price_tracker.extractor import PriceExtractor
from price_tracker.models import Product, ScrapeResult
from price_tracker.notifier import BaseNotifier
from price_tracker.scraper import WebScraper
from price_tracker.tracker import PriceTracker


class MockNotifier(BaseNotifier):
    def __init__(self):
        self.sent_alerts = []

    def notify(self, alert):
        self.sent_alerts.append(alert)
        return True


def test_tracker_target_reached_and_all_time_low(tmp_path):
    db = Database(db_path=tmp_path / "test.db")
    product_id = db.add_product(
        Product(
            name="Smart TV",
            url="https://example.com/tv",
            target_price=500.0,
            current_price=600.0,
            lowest_price=550.0,
            highest_price=650.0,
        )
    )

    scraper = MagicMock(spec=WebScraper)
    scraper.fetch_html.return_value = ("<html>dummy</html>", None)

    extractor = MagicMock(spec=PriceExtractor)
    extractor.extract.return_value = ScrapeResult(
        success=True, price=450.0, currency="USD", in_stock=True, title="Smart TV"
    )

    notifier = MockNotifier()
    tracker = PriceTracker(db=db, scraper=scraper, extractor=extractor, notifier=notifier)

    product, alerts, error = tracker.check_product(product_id)
    assert error is None
    assert product is not None
    assert product.current_price == 450.0
    assert product.lowest_price == 450.0

    types = [a.alert_type for a in alerts]
    assert "TARGET_REACHED" in types
    assert "ALL_TIME_LOW" in types
    assert len(notifier.sent_alerts) == len(alerts)


def test_tracker_back_in_stock(tmp_path):
    db = Database(db_path=tmp_path / "test.db")
    product_id = db.add_product(
        Product(
            name="Mechanical Pencil",
            url="https://example.com/pencil",
            current_price=10.0,
            in_stock=False,
        )
    )

    scraper = MagicMock(spec=WebScraper)
    scraper.fetch_html.return_value = ("<html>dummy</html>", None)

    extractor = MagicMock(spec=PriceExtractor)
    extractor.extract.return_value = ScrapeResult(
        success=True, price=10.0, currency="USD", in_stock=True, title="Mechanical Pencil"
    )

    notifier = MockNotifier()
    tracker = PriceTracker(db=db, scraper=scraper, extractor=extractor, notifier=notifier)

    product, alerts, error = tracker.check_product(product_id)
    assert error is None
    assert product.in_stock is True
    assert any(a.alert_type == "BACK_IN_STOCK" for a in alerts)


def test_tracker_fetch_error(tmp_path):
    db = Database(db_path=tmp_path / "test.db")
    product_id = db.add_product(Product(name="Item", url="https://example.com/fail"))

    scraper = MagicMock(spec=WebScraper)
    scraper.fetch_html.return_value = ("", "Network connection error")

    tracker = PriceTracker(db=db, scraper=scraper)
    product, alerts, error = tracker.check_product(product_id)

    assert error == "Network connection error"
    assert len(alerts) == 0


def test_tracker_check_all(tmp_path):
    db = Database(db_path=tmp_path / "test.db")
    db.add_product(Product(name="P1", url="https://example.com/p1"))
    db.add_product(Product(name="P2", url="https://example.com/p2"))

    scraper = MagicMock(spec=WebScraper)
    scraper.fetch_html.return_value = ("<html>test</html>", None)

    extractor = MagicMock(spec=PriceExtractor)
    extractor.extract.return_value = ScrapeResult(success=True, price=29.99, currency="USD", in_stock=True)

    tracker = PriceTracker(db=db, scraper=scraper, extractor=extractor)
    results = tracker.check_all(delay_seconds=0.0)

    assert len(results) == 2
    assert results[0][0].current_price == 29.99
    assert results[1][0].current_price == 29.99
