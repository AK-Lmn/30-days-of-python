import csv
import json
from pathlib import Path
from price_tracker.config import get_export_dir
from price_tracker.models import PriceRecord, Product, ProductStats


class Exporter:
    def __init__(self, export_dir: Path | str | None = None):
        self.export_dir = Path(export_dir) if export_dir else get_export_dir()
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def export_json(
        self,
        products: list[Product],
        history_map: dict[int, list[PriceRecord]] | None = None,
        file_name: str = "products_export.json",
    ) -> Path:
        target = self.export_dir / file_name
        data = []
        for p in products:
            item = {
                "id": p.id,
                "name": p.name,
                "url": p.url,
                "selector": p.selector,
                "target_price": p.target_price,
                "current_price": p.current_price,
                "lowest_price": p.lowest_price,
                "highest_price": p.highest_price,
                "currency": p.currency,
                "in_stock": p.in_stock,
                "tag": p.tag,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
                "last_checked": p.last_checked,
            }
            if history_map and p.id in history_map:
                item["history"] = [
                    {
                        "price": r.price,
                        "currency": r.currency,
                        "in_stock": r.in_stock,
                        "recorded_at": r.recorded_at,
                        "note": r.note,
                    }
                    for r in history_map[p.id]
                ]
            data.append(item)

        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return target

    def export_csv(self, products: list[Product], file_name: str = "products_export.csv") -> Path:
        target = self.export_dir / file_name
        fieldnames = [
            "id",
            "name",
            "url",
            "target_price",
            "current_price",
            "lowest_price",
            "highest_price",
            "currency",
            "in_stock",
            "tag",
            "last_checked",
        ]

        with open(target, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for p in products:
                writer.writerow(
                    {
                        "id": p.id,
                        "name": p.name,
                        "url": p.url,
                        "target_price": p.target_price,
                        "current_price": p.current_price,
                        "lowest_price": p.lowest_price,
                        "highest_price": p.highest_price,
                        "currency": p.currency,
                        "in_stock": "Yes" if p.in_stock else "No",
                        "tag": p.tag,
                        "last_checked": p.last_checked or "",
                    }
                )
        return target

    def export_markdown(
        self,
        products: list[Product],
        stats_map: dict[int, ProductStats] | None = None,
        file_name: str = "price_report.md",
    ) -> Path:
        target = self.export_dir / file_name
        lines = [
            "# Price Tracker Report",
            "",
            f"**Total Tracked Products:** {len(products)}",
            "",
            "| ID | Name | Current Price | Target Price | All-Time Low | In Stock | Tag |",
            "|---:|---|---:|---:|---:|---|---|",
        ]

        for p in products:
            curr = f"{p.currency} {p.current_price:.2f}" if p.current_price is not None else "N/A"
            target_str = f"{p.currency} {p.target_price:.2f}" if p.target_price is not None else "N/A"
            lowest = f"{p.currency} {p.lowest_price:.2f}" if p.lowest_price is not None else "N/A"
            stock = "✅ In Stock" if p.in_stock else "❌ Out"
            lines.append(f"| {p.id} | {p.name} | {curr} | {target_str} | {lowest} | {stock} | {p.tag} |")

        lines.append("")
        with open(target, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return target

    def import_from_json(self, file_path: Path | str) -> list[Product]:
        path = Path(file_path)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        products = []
        for item in data:
            products.append(
                Product(
                    name=item.get("name", "Unnamed Product"),
                    url=item["url"],
                    selector=item.get("selector", ""),
                    target_price=float(item["target_price"]) if item.get("target_price") is not None else None,
                    currency=item.get("currency", "USD"),
                    tag=item.get("tag", ""),
                )
            )
        return products

    def import_from_csv(self, file_path: Path | str) -> list[Product]:
        path = Path(file_path)
        products = []
        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                target_price = None
                if row.get("target_price"):
                    try:
                        target_price = float(row["target_price"])
                    except ValueError:
                        pass
                products.append(
                    Product(
                        name=row.get("name", "Unnamed Product"),
                        url=row["url"],
                        selector=row.get("selector", ""),
                        target_price=target_price,
                        currency=row.get("currency", "USD"),
                        tag=row.get("tag", ""),
                    )
                )
        return products
