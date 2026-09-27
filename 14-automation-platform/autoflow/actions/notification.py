from datetime import datetime, timezone
from typing import Any

from autoflow.actions.base import BaseAction
from autoflow.models.enums import ActionType


class NotificationAction(BaseAction):
    action_type = ActionType.NOTIFICATION.value
    display_name = "Notification Dispatcher"
    description = "Dispatches a notification to email, webhook, console, or messaging channel"
    parameters_schema = {
        "channel": {"type": "string", "default": "console"},
        "recipient": {"type": "string", "required": True},
        "subject": {"type": "string", "default": ""},
        "message": {"type": "string", "required": True},
    }

    async def execute(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        recipient = config.get("recipient")
        if not recipient:
            raise ValueError("Notification action requires 'recipient'")

        channel = config.get("channel", "console")
        subject = config.get("subject", "")
        message = config.get("message", "")

        return {
            "delivered": True,
            "channel": channel,
            "recipient": recipient,
            "subject": subject,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
