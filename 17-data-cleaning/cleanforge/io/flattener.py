from typing import Any


def flatten_dict(data: dict[str, Any], parent_key: str = "", sep: str = ".") -> dict[str, Any]:
    items: list[tuple[str, Any]] = []
    for k, v in data.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else str(k)
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            if all(not isinstance(i, (dict, list)) for i in v):
                items.append((new_key, ", ".join(str(i) for i in v)))
            else:
                for idx, item in enumerate(v):
                    item_key = f"{new_key}{sep}{idx}"
                    if isinstance(item, dict):
                        items.extend(flatten_dict(item, item_key, sep=sep).items())
                    else:
                        items.append((item_key, item))
        else:
            items.append((new_key, v))
    return dict(items)


def flatten_records(records: list[dict[str, Any]], sep: str = ".") -> list[dict[str, Any]]:
    return [flatten_dict(record, sep=sep) if isinstance(record, dict) else record for record in records]
