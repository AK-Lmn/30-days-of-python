from unittest.mock import patch
from price_tracker.models import PriceAlert
from price_tracker.notifier import CompositeNotifier, ConsoleNotifier, FileNotifier, WebhookNotifier


def test_console_notifier():
    notifier = ConsoleNotifier()
    alert = PriceAlert(
        product_id=1,
        product_name="Phone",
        alert_type="PRICE_DROP",
        new_price=499.0,
        message="Price dropped",
    )
    assert notifier.notify(alert) is True


def test_file_notifier(tmp_path):
    log_file = tmp_path / "alerts.log"
    notifier = FileNotifier(log_path=log_file)
    alert = PriceAlert(
        product_id=1,
        product_name="Phone",
        alert_type="PRICE_DROP",
        new_price=499.0,
        message="Price dropped",
    )
    assert notifier.notify(alert) is True
    assert log_file.exists()

    content = log_file.read_text(encoding="utf-8")
    assert "PRICE_DROP" in content
    assert "Phone" in content
    assert "499.00" in content


def test_webhook_notifier():
    with patch("httpx.Client.post") as mock_post:
        mock_post.return_value.is_success = True
        notifier = WebhookNotifier(webhook_url="https://discord.com/api/webhooks/dummy")
        alert = PriceAlert(
            product_id=1,
            product_name="Laptop",
            alert_type="TARGET_REACHED",
            new_price=899.0,
            message="Target reached",
        )
        assert notifier.notify(alert) is True
        assert mock_post.called


def test_composite_notifier(tmp_path):
    log_file = tmp_path / "alerts.log"
    f_notifier = FileNotifier(log_path=log_file)
    c_notifier = ConsoleNotifier()

    composite = CompositeNotifier([f_notifier, c_notifier])
    alert = PriceAlert(
        product_id=2,
        product_name="Monitor",
        alert_type="ALL_TIME_LOW",
        new_price=199.0,
        message="All time low",
    )
    assert composite.notify(alert) is True
    assert log_file.exists()
