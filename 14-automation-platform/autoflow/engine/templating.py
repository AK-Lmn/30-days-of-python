from typing import Any
from jinja2 import Undefined
from jinja2.nativetypes import NativeEnvironment


class SilentUndefined(Undefined):
    def _fail_with_undefined_error(self, *args: Any, **kwargs: Any) -> Any:
        return ""


env = NativeEnvironment(undefined=SilentUndefined)


def extract_context_value(path: str, context: dict[str, Any]) -> Any:
    parts = path.strip().split(".")
    current: Any = context
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        elif hasattr(current, part):
            current = getattr(current, part)
        else:
            return None
        if current is None:
            break
    return current


def render_template_value(value: Any, context: dict[str, Any]) -> Any:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("{{") and stripped.endswith("}}") and "{{" not in stripped[2:-2]:
            expr = stripped[2:-2].strip()
            if "|" not in expr:
                val = extract_context_value(expr, context)
                if val is not None:
                    return val
        if "{{" in value and "}}" in value:
            try:
                template = env.from_string(value)
                return template.render(**context)
            except Exception:
                return value
        return value
    elif isinstance(value, dict):
        return {k: render_template_value(v, context) for k, v in value.items()}
    elif isinstance(value, list):
        return [render_template_value(item, context) for item in value]
    return value
