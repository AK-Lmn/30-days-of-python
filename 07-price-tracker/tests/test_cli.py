import os
from unittest.mock import patch
from click.testing import CliRunner
from price_tracker.cli import main
from price_tracker.db import Database
from price_tracker.models import Product


def test_cli_add_and_list(tmp_path):
    db_file = tmp_path / "test.db"
    with patch.dict(os.environ, {"PRICE_TRACKER_DB": str(db_file)}):
        runner = CliRunner()
        with patch("price_tracker.scraper.WebScraper.fetch_html") as mock_fetch:
            mock_fetch.return_value = (
                "<html><span class='price'>$79.99</span><h1>Gaming Headset</h1></html>",
                None,
            )
            result = runner.invoke(
                main,
                ["add", "https://example.com/headset", "--name", "Gaming Headset", "--target-price", "70.0"],
            )
            assert result.exit_code == 0
            assert "Added product Gaming Headset" in result.output

        list_res = runner.invoke(main, ["list"])
        assert list_res.exit_code == 0
        assert "Gaming Headset" in list_res.output
        assert "79.99" in list_res.output


def test_cli_check_and_stats(tmp_path):
    db_file = tmp_path / "test.db"
    db = Database(db_path=db_file)
    db.add_product(
        Product(
            name="Laptop",
            url="https://example.com/laptop",
            target_price=1000.0,
            current_price=1200.0,
        )
    )

    with patch.dict(os.environ, {"PRICE_TRACKER_DB": str(db_file)}):
        runner = CliRunner()
        with patch("price_tracker.scraper.WebScraper.fetch_html") as mock_fetch:
            mock_fetch.return_value = (
                "<html><span class='price'>$950.00</span></html>",
                None,
            )
            check_res = runner.invoke(main, ["check", "1"])
            assert check_res.exit_code == 0
            assert "950.00" in check_res.output

        stats_res = runner.invoke(main, ["stats", "1"])
        assert stats_res.exit_code == 0
        assert "Laptop" in stats_res.output
        assert "950.00" in stats_res.output


def test_cli_history_and_alerts(tmp_path):
    db_file = tmp_path / "test.db"
    db = Database(db_path=db_file)
    db.add_product(Product(name="Watch", url="https://example.com/watch"))

    with patch.dict(os.environ, {"PRICE_TRACKER_DB": str(db_file)}):
        runner = CliRunner()
        with patch("price_tracker.scraper.WebScraper.fetch_html") as mock_fetch:
            mock_fetch.return_value = ("<html><span class='price'>$150.00</span></html>", None)
            runner.invoke(main, ["check", "1"])

        hist_res = runner.invoke(main, ["history", "1"])
        assert hist_res.exit_code == 0
        assert "150.00" in hist_res.output

        alert_res = runner.invoke(main, ["alerts"])
        assert alert_res.exit_code == 0


def test_cli_delete(tmp_path):
    db_file = tmp_path / "test.db"
    db = Database(db_path=db_file)
    pid = db.add_product(Product(name="ItemToDelete", url="https://example.com/del"))

    with patch.dict(os.environ, {"PRICE_TRACKER_DB": str(db_file)}):
        runner = CliRunner()
        del_res = runner.invoke(main, ["delete", str(pid), "--yes"])
        assert del_res.exit_code == 0
        assert f"Successfully deleted product #{pid}" in del_res.output
