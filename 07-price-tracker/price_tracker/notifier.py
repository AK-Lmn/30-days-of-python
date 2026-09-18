from abc import ABC, abstractmethod
from pathlib import Path
import httpx
from rich.console import Console
from price_tracker.config import get_base_dir
from price_tracker.models import PriceAlert


class BaseNotifier(ABC):
    @abstractmethod
    def notify(self, alert: PriceAlert) -> bool:
        pass


class ConsoleNotifier(BaseNotifier):
    def __init__(self, console: Console | None = None):
        self.console = console or Console()

    def notify(self, alert: PriceAlert) -> bool:
        color = "bold green" if "REACHED" in alert.alert_type else "bold yellow"
        self.console.print(
            f"[{color}][ALERT] {alert.alert_type}: {alert.product_name}[/{color}] "
            f"Now {alert.currency} {alert.new_price:.2f} ({alert.message})"
        )
        return True


class FileNotifier(BaseNotifier):
    def __init__(self, log_path: Path | str | None = None):
        if log_path:
            self.log_path = Path(log_path)
        else:
            self.log_path = get_base_dir() / "alerts.log"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def notify(self, alert: PriceAlert) -> bool:
        try:
            line = (
                f"[{alert.triggered_at}] {alert.alert_type} | {alert.product_name} | "
                f"{alert.currency} {alert.new_price:.2f} | {alert.message}\n"
            )
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(line)
            return True
        except Exception:
            return False


class WebhookNotifier(BaseNotifier):
    def __init__(self, webhook_url: str, timeout: float = 10.0):
        self.webhook_url = webhook_url
        self.timeout = timeout

    def notify(self, alert: PriceAlert) -> bool:
        if not self.webhook_url:
            return False

        payload = {
            "content": f"🚨 **Price Alert: {alert.product_name}**\n{alert.message}",
            "embeds": [
                {
                    "title": f"{alert.alert_type} - {alert.product_name}",
                    "description": alert.message,
                    "fields": [
                        {"name": "Current Price", "value": f"{alert.currency} {alert.new_price:.2f}", "inline": True},
                        {
                            "name": "Previous Price",
                            "value": f"{alert.currency} {alert.old_price:.2f}" if alert.old_price else "N/A",
                            "inline": True,
                        },
                        {
                            "name": "Target Price",
                            "value": f"{alert.currency} {alert.target_price:.2f}" if alert.target_price else "N/A",
                            "inline": True,
                        },
                    ],
                }
            ],
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(self.webhook_url, json=payload)
                return res.is_success
        except Exception:
            return False


class CompositeNotifier(BaseNotifier):
    def __init__(self, notifiers: list[BaseNotifier] | None = None):
        self.notifiers = notifiers or []

    def add_notifier(self, notifier: BaseNotifier) -> None:
        self.notifiers.append(notifier)

    def notify(self, alert: PriceAlert) -> bool:
        results = [n.notify(alert) for n in self.notifiers]
        return any(results) if results else False
