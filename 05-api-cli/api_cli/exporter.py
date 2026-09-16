import csv
import io
import json
from pathlib import Path
from typing import Any, List, Optional, Union


def flatten_value(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, (dict, list)):
        return json.dumps(val)
    return str(val)


def data_to_json_str(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def data_to_csv_str(data: Any) -> str:
    output = io.StringIO()
    if isinstance(data, list) and data and all(isinstance(i, dict) for i in data):
        keys: List[str] = []
        for item in data:
            for k in item.keys():
                if k not in keys:
                    keys.append(k)
        writer = csv.DictWriter(output, fieldnames=keys, lineterminator="\n")
        writer.writeheader()
        for item in data:
            row = {k: flatten_value(item.get(k)) for k in keys}
            writer.writerow(row)
    elif isinstance(data, dict):
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(["Key", "Value"])
        for k, v in data.items():
            writer.writerow([str(k), flatten_value(v)])
    elif isinstance(data, list):
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(["Index", "Value"])
        for idx, v in enumerate(data):
            writer.writerow([idx, flatten_value(v)])
    else:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(["Value"])
        writer.writerow([flatten_value(data)])
    return output.getvalue()


def data_to_markdown_str(data: Any) -> str:
    if isinstance(data, list) and data and all(isinstance(i, dict) for i in data):
        keys: List[str] = []
        for item in data:
            for k in item.keys():
                if k not in keys:
                    keys.append(k)
        header_row = "| " + " | ".join(keys) + " |"
        sep_row = "| " + " | ".join(["---"] * len(keys)) + " |"
        rows = [header_row, sep_row]
        for item in data:
            row_cells = [flatten_value(item.get(k)).replace("|", "\\|").replace("\n", " ") for k in keys]
            rows.append("| " + " | ".join(row_cells) + " |")
        return "\n".join(rows) + "\n"

    if isinstance(data, dict):
        rows = ["| Key | Value |", "| --- | --- |"]
        for k, v in data.items():
            val_str = flatten_value(v).replace("|", "\\|").replace("\n", " ")
            rows.append(f"| {k} | {val_str} |")
        return "\n".join(rows) + "\n"

    if isinstance(data, list):
        rows = ["| Index | Value |", "| --- | --- |"]
        for idx, v in enumerate(data):
            val_str = flatten_value(v).replace("|", "\\|").replace("\n", " ")
            rows.append(f"| {idx} | {val_str} |")
        return "\n".join(rows) + "\n"

    return str(data) + "\n"


def export_data(data: Any, target_path: Union[str, Path], format_hint: Optional[str] = None) -> Path:
    dest = Path(target_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    ext = dest.suffix.lower().lstrip(".")
    resolved_format = (format_hint or ext or "json").lower()

    if resolved_format == "csv":
        content = data_to_csv_str(data)
    elif resolved_format in ("md", "markdown"):
        content = data_to_markdown_str(data)
    elif resolved_format in ("txt", "text", "raw"):
        content = str(data) if not isinstance(data, (dict, list)) else json.dumps(data, indent=2)
    else:
        content = data_to_json_str(data)

    dest.write_text(content, encoding="utf-8")
    return dest.resolve()
