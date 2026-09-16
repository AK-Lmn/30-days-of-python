from unittest.mock import MagicMock
import httpx
from website_monitor.models import CheckResult, MonitorTarget
from website_monitor.notifier import (
    format_slack_payload,
    format_discord_payload,
    format_generic_payload,
    send_webhook,
    NotificationManager,
)


def test_payload_formatters():
    slack = format_slack_payload("OUTAGE", "API", "https://api.test", "Error")
    assert "OUTAGE" in slack["text"]
    assert slack["attachments"][0]["color"] == "#dc3545"

    discord = format_discord_payload("RECOVERY", "API", "https://api.test", "Fixed")
    assert "**[RECOVERY]**" in discord["content"]

    generic = format_generic_payload("OUTAGE", "API", "https://api.test", "Error")
    assert generic["event"] == "OUTAGE"
    assert generic["target_name"] == "API"


def test_send_webhook_success():
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.return_value = mock_resp

    ok = send_webhook(
        "https://webhook.site/test",
        "OUTAGE",
        "Target",
        "https://test.org",
        "Message",
        client=mock_client,
    )
    assert ok is True
    assert mock_client.post.called


def test_send_webhook_failure():
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.post.side_effect = Exception("network error")

    ok = send_webhook(
        "https://webhook.site/test",
        "OUTAGE",
        "Target",
        "https://test.org",
        "Message",
        client=mock_client,
    )
    assert ok is False


def test_notification_manager_state_transitions():
    manager = NotificationManager(consecutive_failures_threshold=2)
    target = MonitorTarget(id=1, url="https://api.test", name="API")

    fail1 = CheckResult(target_id=1, is_up=False, response_time_ms=10.0, error_message="500")
    event1 = manager.handle_check(fail1, target)
    assert event1 is None
    assert manager.failure_counts[1] == 1

    fail2 = CheckResult(target_id=1, is_up=False, response_time_ms=10.0, error_message="500")
    event2 = manager.handle_check(fail2, target)
    assert event2 == "OUTAGE"
    assert manager.alerted_down[1] is True

    fail3 = CheckResult(target_id=1, is_up=False, response_time_ms=10.0, error_message="500")
    event3 = manager.handle_check(fail3, target)
    assert event3 is None

    success = CheckResult(target_id=1, is_up=True, response_time_ms=45.0, status_code=200)
    event_rec = manager.handle_check(success, target)
    assert event_rec == "RECOVERY"
    assert manager.alerted_down[1] is False
    assert manager.failure_counts[1] == 0
