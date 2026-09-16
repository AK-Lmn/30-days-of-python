from typing import Any, List, Optional
import jmespath


class FilterError(Exception):
    pass


def apply_jmespath_filter(data: Any, expression: str) -> Any:
    if not expression or not expression.strip():
        return data
    try:
        return jmespath.search(expression, data)
    except Exception as exc:
        raise FilterError(f"JMESPath query failed: {str(exc)}") from exc


def pick_fields(data: Any, fields: List[str]) -> Any:
    if not fields:
        return data
    clean_fields = [f.strip() for f in fields if f.strip()]
    if not clean_fields:
        return data

    if isinstance(data, list):
        filtered_list = []
        for item in data:
            if isinstance(item, dict):
                filtered_list.append({k: item.get(k) for k in clean_fields if k in item})
            else:
                filtered_list.append(item)
        return filtered_list

    if isinstance(data, dict):
        return {k: data.get(k) for k in clean_fields if k in data}

    return data


def filter_payload(data: Any, expression: Optional[str] = None, fields: Optional[List[str]] = None) -> Any:
    result = data
    if expression:
        result = apply_jmespath_filter(result, expression)
    if fields:
        result = pick_fields(result, fields)
    return result
