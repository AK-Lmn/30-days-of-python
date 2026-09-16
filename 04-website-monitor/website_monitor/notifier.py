from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx

from website_monitor.config import DEFAULT_CONSECUTIVE_FAILURES_BEFORE_ALERT, DEFAULT_SSL_WARNING_DAYS
from website_monitor.models import CheckResult, MonitorTarget


def format_slack_payload(event_type: str, target_name: str, target_url: str, message: str) -> Dict[str, Any]:
    color = "#36a64f" if event_type == "RECOVERY" else "#dc3545"
    return {
        "text": f"[{event_type}] {target_name} ({target_url})",
        "attachments": [
            {
                "color": color,
                "title": f"Website Monitor Alert: {event_type}",
                "text": message,
                "fields": [
                    {"title": "Target", "value": target_name, "short": True},
                    {"title": "URL", "value": target_url, "short": True},
                ],
                "ts": int(datetime.now(timezone.utc).timestamp()),
            }
        ],
    }


def format_discord_payload(event_type: str, target_name: str, target_url: str, message: str) -> Dict[str, Any]:
    color = 0x28A745 if event_type == "RECOVERY" else 0xDC3545
    return {
        "content": f"**[{event_type}]** {target_name}",
        "embeds": [
            {
                "title": f"Website Monitor Notification",
                "description": message,
                "color": color,
                "fields": [
                    {"name": "Target", "value": target_name, "inline": True},
                    {"name": "URL", "value": target_url, "inline": True},
                ],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ],
    }


def format_generic_payload(event_type: str, target_name: str, target_url: str, message: str) -> Dict[str, Any]:
    return {
        "event": event_type,
        "target_name": target_name,
        "target_url": target_url,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def send_webhook(
    webhook_url: str,
    event_type: str,
    target_name: str,
    target_url: str,
    message: str,
    provider: str = "generic",
    client: Optional[httpx.Client] = None,
) -> bool:
    provider_clean = provider.strip().lower()
    if provider_clean == "slack":
        payload = format_slack_payload(event_type, target_name, target_url, message)
    elif provider_clean == "discord":
        payload = format_discord_payload(event_type, target_name, target_url, message)
    else:
        payload = format_generic_payload(event_type, target_name, target_url, message)

    try:
        if client:
            resp = client.post(webhook_url, json=payload, timeout=5.0)
            return resp.status_code < 400
        with httpx.Client(timeout=5.0) as c:
            resp = c.post(webhook_url, json=payload)
            return resp.status_code < 400
    except Exception:
        return False


class NotificationManager:
    def __init__(
        self,
        webhook_urls: Optional[List[str]] = None,
        consecutive_failures_threshold: int = DEFAULT_CONSECUTIVE_FAILURES_BEFORE_ALERT,
        ssl_warning_days: int = DEFAULT_SSL_WARNING_DAYS,
    ):
        self.webhook_urls = webhook_urls or []
        self.consecutive_failures_threshold = consecutive_failures_threshold
        self.ssl_warning_days = ssl_warning_days
        self.failure_counts: Dict[int, int] = {}
        self.alerted_down: Dict[int, bool] = {}
        self.ssl_alerted: Dict[int, bool] = {}

    def handle_check(
        self,
        result: CheckResult,
        target: MonitorTarget,
        client: Optional[httpx.Client] = None,
    ) -> Optional[str]:
        target_id = target.id or 0
        current_fails = self.failure_counts.get(target_id, 0)
        event: Optional[str] = None
        message: Optional[str] = None

        if result.is_up:
            if self.alerted_down.get(target_id, False):
                event = "RECOVERY"
                message = f"{target.name} has recovered. Response time: {result.response_time_ms:.1f}ms"
                self.alerted_down[target_id] = False
            self.failure_counts[target_id] = 0
        else:
            current_fails += 1
            self.failure_counts[target_id] = current_fails
            if current_fails >= self.consecutive_failures_threshold and not self.alerted_down.get(target_id, False):
                event = "OUTAGE"
                reason = result.error_message or "Unknown failure"
                message = f"{target.name} is DOWN! Reason: {reason} (failed {current_fails} consecutive checks)"
                self.alerted_down[target_id] = True

        if (
            result.ssl_days_left is not None
            and result.ssl_days_left <= self.ssl_warning_days
            and not self.ssl_alerted.get(target_id, False)
        ):
            ssl_event = "SSL_EXPIRING"
            ssl_message = f"SSL Certificate for {target.name} ({target.url}) expires in {result.ssl_days_left} days!"
            self.ssl_alerted[target_id] = True
            for url in self.webhook_urls:
                provider = "slack" if "slack.com" in url else ("discord" if "discord.com" in url else "generic")
                send_webhook(url, ssl_event, target.name, target.url, ssl_message, provider=provider, client=client)

        if event and message:
            for url in self.webhook_urls:
                provider = "slack" if "slack.com" in url else ("discord" if "discord.com" in url else "generic")
                send_webhook(url, event, target.name, target.url, message, provider=provider, client=client)

        return event
