from typing import Any
import httpx

from autoflow.actions.base import BaseAction
from autoflow.models.enums import ActionType


class HttpAction(BaseAction):
    action_type = ActionType.HTTP_REQUEST.value
    display_name = "HTTP Request"
    description = "Sends an HTTP request to an external API endpoint"
    parameters_schema = {
        "url": {"type": "string", "required": True},
        "method": {"type": "string", "default": "GET"},
        "headers": {"type": "object", "default": {}},
        "params": {"type": "object", "default": {}},
        "json_body": {"type": "any", "default": None},
        "timeout": {"type": "number", "default": 30.0},
    }

    async def execute(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        url = config.get("url")
        if not url:
            raise ValueError("HTTP action requires 'url'")

        method = config.get("method", "GET").upper()
        headers = config.get("headers", {})
        params = config.get("params", {})
        json_body = config.get("json_body")
        timeout = float(config.get("timeout", 30.0))

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_body,
            )

            try:
                body = response.json()
            except Exception:
                body = response.text

            is_success = 200 <= response.status_code < 300
            if not is_success:
                raise RuntimeError(f"HTTP request failed with status {response.status_code}: {body}")

            return {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "data": body,
            }
