from price_tracker.db import Database
from price_tracker.models import PriceAlert, PriceRecord, Product


def test_product_crud(tmp_path):
    db_file = tmp_path / "test.db"
    db = Database(db_path=db_file)

    product = Product(
        name="Noise Cancelling Headphones",
        url="https://example.com/headphones",
        target_price=150.0,
        currency="USD",
        tag="Electronics",
    )
    product_id = db.add_product(product)
    assert product_id > 0

    fetched = db.get_product(product_id)
    assert fetched is not None
    assert fetched.name == "Noise Cancelling Headphones"
    assert fetched.url == "https://example.com/headphones"
    assert fetched.target_price == 150.0

    by_url = db.get_product_by_url("https://example.com/headphones")
    assert by_url is not None
    assert by_url.id == product_id

    fetched.name = "Upgraded Headphones"
    fetched.current_price = 145.0
    updated = db.update_product(fetched)
    assert updated is True

    updated_product = db.get_product(product_id)
    assert updated_product.name == "Upgraded Headphones"
    assert updated_product.current_price == 145.0

    deleted = db.delete_product(product_id)
    assert deleted is True
    assert db.get_product(product_id) is None


def test_list_products_filtering(tmp_path):
    db_file = tmp_path / "test.db"
    db = Database(db_path=db_file)

    db.add_product(Product(name="Book A", url="https://example.com/a", tag="Books", in_stock=True))
    db.add_product(Product(name="Book B", url="https://example.com/b", tag="Books", in_stock=False))
    db.add_product(Product(name="Gadget", url="https://example.com/g", tag="Tech", in_stock=True))

    all_products = db.list_products()
    assert len(all_products) == 3

    books = db.list_products(tag="Books")
    assert len(books) == 2

    in_stock_books = db.list_products(tag="Books", in_stock=True)
    assert len(in_stock_books) == 1
    assert in_stock_books[0].name == "Book A"


def test_price_history_and_stats(tmp_path):
    db_file = tmp_path / "test.db"
    db = Database(db_path=db_file)

    product_id = db.add_product(Product(name="Espresso Machine", url="https://example.com/coffee", target_price=200.0))

    db.add_price_record(PriceRecord(product_id=product_id, price=250.0))
    db.add_price_record(PriceRecord(product_id=product_id, price=220.0))
    db.add_price_record(PriceRecord(product_id=product_id, price=190.0))

    history = db.get_price_history(product_id)
    assert len(history) == 3
    assert [h.price for h in history] == [250.0, 220.0, 190.0]

    stats = db.get_product_stats(product_id)
    assert stats is not None
    assert stats.current_price == 190.0
    assert stats.lowest_price == 190.0
    assert stats.highest_price == 250.0
    assert stats.average_price == 220.0
    assert stats.records_count == 3
    assert stats.price_change_amount == -60.0
    assert stats.price_change_percentage == -24.0


def test_alerts_logging_and_clearing(tmp_path):
    db_file = tmp_path / "test.db"
    db = Database(db_path=db_file)

    product_id = db.add_product(Product(name="Tablet", url="https://example.com/tab"))

    alert = PriceAlert(
        product_id=product_id,
        product_name="Tablet",
        alert_type="PRICE_DROP",
        old_price=300.0,
        new_price=250.0,
        drop_amount=50.0,
        drop_percentage=16.67,
        message="Price dropped by 16.7%",
    )
    alert_id = db.add_alert(alert)
    assert alert_id > 0

    alerts = db.get_alerts(product_id=product_id)
    assert len(alerts) == 1
    assert alerts[0].alert_type == "PRICE_DROP"
    assert alerts[0].drop_amount == 50.0

    cleared = db.clear_alerts(product_id)
    assert cleared == 1
    assert len(db.get_alerts(product_id=product_id)) == 0
