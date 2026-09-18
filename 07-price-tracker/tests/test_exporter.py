import json
from price_tracker.exporter import Exporter
from price_tracker.models import PriceRecord, Product


def test_export_and_import_json(tmp_path):
    exporter = Exporter(export_dir=tmp_path)
    products = [
        Product(
            id=1,
            name="Keyboard",
            url="https://example.com/kb",
            target_price=80.0,
            current_price=75.0,
            lowest_price=70.0,
            highest_price=90.0,
            currency="USD",
            in_stock=True,
            tag="Tech",
        )
    ]
    history_map = {
        1: [PriceRecord(product_id=1, price=90.0), PriceRecord(product_id=1, price=75.0)]
    }

    export_path = exporter.export_json(products, history_map, file_name="out.json")
    assert export_path.exists()

    with open(export_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["name"] == "Keyboard"
    assert len(data[0]["history"]) == 2

    imported = exporter.import_from_json(export_path)
    assert len(imported) == 1
    assert imported[0].name == "Keyboard"
    assert imported[0].target_price == 80.0


def test_export_and_import_csv(tmp_path):
    exporter = Exporter(export_dir=tmp_path)
    products = [
        Product(
            id=1,
            name="Mouse",
            url="https://example.com/mouse",
            target_price=25.0,
            current_price=22.5,
            currency="USD",
            in_stock=True,
            tag="Tech",
        )
    ]

    export_path = exporter.export_csv(products, file_name="out.csv")
    assert export_path.exists()

    imported = exporter.import_from_csv(export_path)
    assert len(imported) == 1
    assert imported[0].name == "Mouse"
    assert imported[0].target_price == 25.0


def test_export_markdown(tmp_path):
    exporter = Exporter(export_dir=tmp_path)
    products = [
        Product(
            id=1,
            name="Monitor",
            url="https://example.com/monitor",
            target_price=200.0,
            current_price=189.99,
            currency="USD",
            in_stock=True,
            tag="Display",
        )
    ]

    export_path = exporter.export_markdown(products, file_name="report.md")
    assert export_path.exists()

    content = export_path.read_text(encoding="utf-8")
    assert "# Price Tracker Report" in content
    assert "Monitor" in content
    assert "189.99" in content
