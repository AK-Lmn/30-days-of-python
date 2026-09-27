from typing import Any

from autoflow.actions.base import BaseAction
from autoflow.engine.templating import extract_context_value, render_template_value
from autoflow.models.enums import ActionType


class TransformAction(BaseAction):
    action_type = ActionType.TRANSFORM.value
    display_name = "Data Transform"
    description = "Transforms and structures data using field mapping and projection"
    parameters_schema = {
        "mapping": {"type": "object", "default": {}},
        "pick_keys": {"type": "array", "default": []},
        "set_constants": {"type": "object", "default": {}},
    }

    async def execute(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        mapping = config.get("mapping", {})
        pick_keys = config.get("pick_keys", [])
        set_constants = config.get("set_constants", {})

        result: dict[str, Any] = {}

        for target_key, template_or_path in mapping.items():
            if isinstance(template_or_path, str) and not ("{{" in template_or_path and "}}" in template_or_path):
                val = extract_context_value(template_or_path, context)
                if val is not None:
                    result[target_key] = val
                else:
                    result[target_key] = render_template_value(template_or_path, context)
            else:
                result[target_key] = render_template_value(template_or_path, context)

        if pick_keys:
            source = context.get("event", {})
            for key in pick_keys:
                if key in source:
                    result[key] = source[key]

        for const_key, const_val in set_constants.items():
            result[const_key] = const_val

        return {"result": result}
