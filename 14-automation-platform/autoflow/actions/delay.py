import asyncio
from typing import Any

from autoflow.actions.base import BaseAction
from autoflow.models.enums import ActionType


class DelayAction(BaseAction):
    action_type = ActionType.DELAY.value
    display_name = "Delay Wait"
    description = "Asynchronously pauses execution for a designated duration"
    parameters_schema = {
        "seconds": {"type": "number", "default": 1.0, "maximum": 60.0},
    }

    async def execute(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        seconds = float(config.get("seconds", 1.0))
        clamped_seconds = max(0.0, min(seconds, 60.0))
        if clamped_seconds > 0:
            await asyncio.sleep(clamped_seconds)

        return {"delayed_seconds": clamped_seconds}
