import csv
import json
from pathlib import Path
import sqlite3
from typing import Any


class DataExporter:
    @staticmethod
    def ensure_parent_dir(file_path: Path) -> Path:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        return file_path

    @classmethod
    def export_json(cls, data: list[dict[str, Any]], target_file: str | Path, indent: int = 2) -> Path:
        path = cls.ensure_parent_dir(Path(target_file))
        with open(path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=indent, ensure_ascii=False)
        return path

    @classmethod
    def export_jsonl(cls, data: list[dict[str, Any]], target_file: str | Path) -> Path:
        path = cls.ensure_parent_dir(Path(target_file))
        with open(path, "w", encoding="utf-8") as file:
            for item in data:
                file.write(json.dumps(item, ensure_ascii=False) + "\n")
        return path

    @classmethod
    def export_csv(cls, data: list[dict[str, Any]], target_file: str | Path) -> Path:
        path = cls.ensure_parent_dir(Path(target_file))
        if not data:
            with open(path, "w", encoding="utf-8", newline="") as file:
                pass
            return path

        headers: list[str] = []
        for item in data:
            for key in item.keys():
                if key not in headers:
                    headers.append(key)

        with open(path, "w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writeheader()
            for row in data:
                formatted_row = {}
                for k, v in row.items():
                    if isinstance(v, (dict, list)):
                        formatted_row[k] = json.dumps(v, ensure_ascii=False)
                    else:
                        formatted_row[k] = "" if v is None else str(v)
                writer.writerow(formatted_row)

        return path

    @classmethod
    def export_markdown(cls, data: list[dict[str, Any]], target_file: str | Path) -> Path:
        path = cls.ensure_parent_dir(Path(target_file))
        if not data:
            with open(path, "w", encoding="utf-8") as file:
                file.write("_No records scraped._\n")
            return path

        headers: list[str] = []
        for item in data:
            for key in item.keys():
                if key not in headers:
                    headers.append(key)

        lines: list[str] = []
        header_line = "| " + " | ".join(headers) + " |"
        separator_line = "| " + " | ".join(["---"] * len(headers)) + " |"
        lines.append(header_line)
        lines.append(separator_line)

        for item in data:
            row_vals = []
            for h in headers:
                val = item.get(h, "")
                if isinstance(val, (dict, list)):
                    cell = json.dumps(val, ensure_ascii=False).replace("|", "\\|")
                else:
                    cell = str(val if val is not None else "").replace("\n", " ").replace("|", "\\|")
                row_vals.append(cell)
            lines.append("| " + " | ".join(row_vals) + " |")

        with open(path, "w", encoding="utf-8") as file:
            file.write("\n".join(lines) + "\n")

        return path

    @classmethod
    def export_sqlite(
        cls,
        data: list[dict[str, Any]],
        target_file: str | Path,
        table_name: str = "scraped_data",
    ) -> Path:
        path = cls.ensure_parent_dir(Path(target_file))
        if not data:
            return path

        headers: list[str] = []
        for item in data:
            for key in item.keys():
                if key not in headers:
                    headers.append(key)

        sanitized_headers = [h.replace(" ", "_").replace("-", "_") for h in headers]

        has_id = any(h.lower() == "id" for h in sanitized_headers)
        if has_id:
            cols_def = ", ".join(
                f'"{col}" INTEGER PRIMARY KEY' if col.lower() == "id" else f'"{col}" TEXT'
                for col in sanitized_headers
            )
        else:
            cols_def = "_row_id INTEGER PRIMARY KEY AUTOINCREMENT, " + ", ".join(f'"{col}" TEXT' for col in sanitized_headers)

        with sqlite3.connect(path) as conn:
            cursor = conn.cursor()
            cursor.execute(f'CREATE TABLE IF NOT EXISTS "{table_name}" ({cols_def});')

            placeholders = ", ".join(["?"] * len(headers))
            col_names = ", ".join(f'"{col}"' for col in sanitized_headers)
            insert_query = f'INSERT INTO "{table_name}" ({col_names}) VALUES ({placeholders})'

            rows_to_insert = []
            for item in data:
                row = []
                for h in headers:
                    val = item.get(h)
                    if isinstance(val, (dict, list)):
                        row.append(json.dumps(val, ensure_ascii=False))
                    elif val is None:
                        row.append(None)
                    else:
                        row.append(str(val))
                rows_to_insert.append(row)

            cursor.executemany(insert_query, rows_to_insert)
            conn.commit()

        return path

    @classmethod
    def export_by_format(
        cls,
        data: list[dict[str, Any]],
        target_file: str | Path,
        format_type: str | None = None,
    ) -> Path:
        path = Path(target_file)
        fmt = (format_type or path.suffix.lstrip(".").lower()).strip()

        if fmt == "json":
            return cls.export_json(data, path)
        elif fmt in ("jsonl", "ndjson"):
            return cls.export_jsonl(data, path)
        elif fmt == "csv":
            return cls.export_csv(data, path)
        elif fmt in ("md", "markdown"):
            return cls.export_markdown(data, path)
        elif fmt in ("sqlite", "db"):
            return cls.export_sqlite(data, path)
        else:
            return cls.export_json(data, path)
