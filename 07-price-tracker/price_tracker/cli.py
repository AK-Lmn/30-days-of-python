import sys
import time
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from price_tracker.chart import format_change, render_ascii_chart, render_sparkline
from price_tracker.config import DEFAULT_CHECK_INTERVAL_SECONDS
from price_tracker.db import Database
from price_tracker.exporter import Exporter
from price_tracker.models import Product
from price_tracker.tracker import PriceTracker

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console(safe_box=True)


@click.group()
def main() -> None:
    pass


@main.command(name="add")
@click.argument("url")
@click.option("--name", "-n", default="", help="Product name")
@click.option("--selector", "-s", default="", help="Custom CSS selector for price")
@click.option("--target-price", "-t", type=float, default=None, help="Target price threshold")
@click.option("--currency", "-c", default="USD", help="Currency code (USD, EUR, GBP, etc.)")
@click.option("--tag", default="", help="Tag or category")
def add_command(url: str, name: str, selector: str, target_price: float | None, currency: str, tag: str) -> None:
    db = Database()
    existing = db.get_product_by_url(url)
    if existing:
        console.print(f"[bold red]Error:[/bold red] Product with URL already exists (ID: {existing.id})")
        sys.exit(1)

    product_name = name or url.split("/")[-1] or "New Product"
    product = Product(
        name=product_name,
        url=url,
        selector=selector,
        target_price=target_price,
        currency=currency.upper(),
        tag=tag,
    )
    product_id = db.add_product(product)
    console.print(f"[bold green]Success:[/bold green] Added product [bold]{product_name}[/bold] with ID {product_id}")

    console.print("[dim]Running initial price check...[/dim]")
    tracker = PriceTracker(db=db)
    updated, alerts, error = tracker.check_product(product_id)
    if error:
        console.print(f"[yellow]Initial check notice:[/yellow] {error}")
    elif updated and updated.current_price is not None:
        console.print(
            f"[bold green]Current Price:[/bold green] {updated.currency} {updated.current_price:.2f} "
            f"({'In Stock' if updated.in_stock else 'Out of Stock'})"
        )


@main.command(name="list")
@click.option("--tag", default=None, help="Filter by tag")
@click.option("--in-stock/--all", default=None, help="Filter by stock status")
def list_command(tag: str | None, in_stock: bool | None) -> None:
    db = Database()
    products = db.list_products(tag=tag, in_stock=in_stock)
    if not products:
        console.print("[yellow]No tracked products found.[/yellow]")
        return

    table = Table(title="Tracked Products", header_style="bold magenta")
    table.add_column("ID", justify="right", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold white", no_wrap=True)
    table.add_column("Current Price", justify="right")
    table.add_column("Lowest", justify="right", style="green")
    table.add_column("Target", justify="right", style="yellow")
    table.add_column("Stock", justify="center")
    table.add_column("Tag", style="dim")
    table.add_column("Trend (Spark)", justify="center")

    for p in products:
        history = db.get_price_history(p.id) if p.id else []
        prices = [r.price for r in history]
        spark = render_sparkline(prices)

        curr_str = f"{p.currency} {p.current_price:.2f}" if p.current_price is not None else "N/A"
        low_str = f"{p.currency} {p.lowest_price:.2f}" if p.lowest_price is not None else "N/A"
        target_str = f"{p.currency} {p.target_price:.2f}" if p.target_price is not None else "─"

        if p.target_price is not None and p.current_price is not None and p.current_price <= p.target_price:
            curr_str = f"[bold green]{curr_str} 🎯[/bold green]"

        stock_str = "[green]In Stock[/green]" if p.in_stock else "[red]Out[/red]"

        table.add_row(
            str(p.id),
            p.name[:35] + ("..." if len(p.name) > 35 else ""),
            curr_str,
            low_str,
            target_str,
            stock_str,
            p.tag or "─",
            spark or "─",
        )

    console.print(table)


@main.command(name="check")
@click.argument("product_id", type=int, required=False)
@click.option("--delay", default=0.5, type=float, help="Delay between checks in seconds")
@click.option("--tag", default=None, help="Filter check by tag")
def check_command(product_id: int | None, delay: float, tag: str | None) -> None:
    db = Database()
    tracker = PriceTracker(db=db)

    if product_id is not None:
        console.print(f"Checking price for product #{product_id}...")
        updated, alerts, error = tracker.check_product(product_id)
        if error:
            console.print(f"[bold red]Check failed:[/bold red] {error}")
            sys.exit(1)
        if updated:
            console.print(
                f"[bold green]Checked:[/bold green] {updated.name} -> "
                f"{updated.currency} {updated.current_price:.2f} "
                f"({'In Stock' if updated.in_stock else 'Out of Stock'})"
            )
            for a in alerts:
                console.print(f"[bold yellow]Alert:[/bold yellow] {a.alert_type} - {a.message}")
        return

    console.print("Checking prices for all products...")
    results = tracker.check_all(tag=tag, delay_seconds=delay)
    if not results:
        console.print("[yellow]No products to check.[/yellow]")
        return

    for prod, alerts, err in results:
        if err:
            console.print(f"[red]Failed #{prod.id} ({prod.name}): {err}[/red]")
        else:
            console.print(
                f"[green]✓ #{prod.id} {prod.name}:[/green] {prod.currency} {prod.current_price:.2f} "
                f"({'In Stock' if prod.in_stock else 'Out of Stock'})"
            )
            for a in alerts:
                console.print(f"  └─ [bold yellow]{a.alert_type}:[/bold yellow] {a.message}")


@main.command(name="history")
@click.argument("product_id", type=int)
@click.option("--limit", "-l", type=int, default=30, help="Maximum records to display")
def history_command(product_id: int, limit: int) -> None:
    db = Database()
    product = db.get_product(product_id)
    if not product:
        console.print(f"[bold red]Error:[/bold red] Product #{product_id} not found.")
        sys.exit(1)

    records = db.get_price_history(product_id, limit=limit)
    if not records:
        console.print(f"[yellow]No price history available for {product.name}.[/yellow]")
        return

    prices = [r.price for r in records]
    chart_output = render_ascii_chart(prices)

    table = Table(title=f"Price History for {product.name}", header_style="bold cyan")
    table.add_column("Timestamp", style="dim")
    table.add_column("Price", justify="right")
    table.add_column("Change", justify="right")
    table.add_column("Stock", justify="center")

    for i, r in enumerate(records):
        prev_price = records[i - 1].price if i > 0 else None
        change_str = format_change(prev_price, r.price, r.currency)
        stock_str = "[green]Yes[/green]" if r.in_stock else "[red]No[/red]"
        table.add_row(
            r.recorded_at[:19].replace("T", " "),
            f"{r.currency} {r.price:.2f}",
            change_str,
            stock_str,
        )

    console.print(table)
    console.print("\n[bold]Historical Trend:[/bold]")
    console.print(chart_output)


@main.command(name="alerts")
@click.option("--product-id", "-p", type=int, default=None, help="Filter by product ID")
@click.option("--limit", "-l", type=int, default=30, help="Maximum alerts to display")
@click.option("--clear", is_flag=True, help="Clear alert history")
def alerts_command(product_id: int | None, limit: int, clear: bool) -> None:
    db = Database()
    if clear:
        cleared = db.clear_alerts(product_id)
        console.print(f"[green]Cleared {cleared} alerts.[/green]")
        return

    alerts = db.get_alerts(product_id=product_id, limit=limit)
    if not alerts:
        console.print("[yellow]No alerts recorded.[/yellow]")
        return

    table = Table(title="Triggered Price Alerts", header_style="bold red")
    table.add_column("Time", style="dim")
    table.add_column("Product", style="bold white")
    table.add_column("Type", style="bold yellow")
    table.add_column("New Price", justify="right", style="green")
    table.add_column("Message")

    for a in alerts:
        table.add_row(
            a.triggered_at[:19].replace("T", " "),
            a.product_name,
            a.alert_type,
            f"{a.currency} {a.new_price:.2f}",
            a.message,
        )

    console.print(table)


@main.command(name="stats")
@click.argument("product_id", type=int)
def stats_command(product_id: int) -> None:
    db = Database()
    stats = db.get_product_stats(product_id)
    if not stats:
        console.print(f"[bold red]Error:[/bold red] Product #{product_id} not found.")
        sys.exit(1)

    product = db.get_product(product_id)
    curr_str = f"{product.currency} {stats.current_price:.2f}" if stats.current_price is not None else "N/A"
    low_str = f"{product.currency} {stats.lowest_price:.2f}" if stats.lowest_price is not None else "N/A"
    high_str = f"{product.currency} {stats.highest_price:.2f}" if stats.highest_price is not None else "N/A"
    avg_str = f"{product.currency} {stats.average_price:.2f}" if stats.average_price is not None else "N/A"
    target_str = f"{product.currency} {product.target_price:.2f}" if product.target_price is not None else "Not set"

    body = (
        f"[bold]Product:[/bold] {stats.product_name} (ID: {product_id})\n"
        f"[bold]Current Price:[/bold] {curr_str}\n"
        f"[bold]Target Price:[/bold] {target_str}\n"
        f"[bold]All-Time Lowest:[/bold] [green]{low_str}[/green]\n"
        f"[bold]All-Time Highest:[/bold] [red]{high_str}[/red]\n"
        f"[bold]Historical Average:[/bold] {avg_str}\n"
        f"[bold]Data Points:[/bold] {stats.records_count}\n"
    )
    if stats.price_change_percentage is not None:
        body += f"[bold]Net Change:[/bold] {stats.price_change_percentage:+.2f}%\n"

    console.print(Panel(body, title=f"Statistics — {stats.product_name}", border_style="cyan"))


@main.command(name="delete")
@click.argument("product_id", type=int)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def delete_command(product_id: int, yes: bool) -> None:
    db = Database()
    product = db.get_product(product_id)
    if not product:
        console.print(f"[bold red]Error:[/bold red] Product #{product_id} not found.")
        sys.exit(1)

    if not yes:
        if not click.confirm(f"Are you sure you want to delete '{product.name}' (ID: {product_id})?"):
            console.print("[dim]Aborted.[/dim]")
            return

    db.delete_product(product_id)
    console.print(f"[green]Successfully deleted product #{product_id}.[/green]")


@main.command(name="export")
@click.option("--format", "-f", "fmt", type=click.Choice(["json", "csv", "md"]), default="json")
@click.option("--output", "-o", default=None, help="Custom output filename")
def export_command(fmt: str, output: str | None) -> None:
    db = Database()
    products = db.list_products()
    if not products:
        console.print("[yellow]No products to export.[/yellow]")
        return

    exporter = Exporter()
    if fmt == "json":
        history_map = {p.id: db.get_price_history(p.id) for p in products if p.id}
        path = exporter.export_json(products, history_map, file_name=output or "products_export.json")
    elif fmt == "csv":
        path = exporter.export_csv(products, file_name=output or "products_export.csv")
    else:
        path = exporter.export_markdown(products, file_name=output or "price_report.md")

    console.print(f"[bold green]Exported {len(products)} products to:[/bold green] {path}")


@main.command(name="import-file")
@click.argument("file_path", type=click.Path(exists=True))
def import_command(file_path: str) -> None:
    exporter = Exporter()
    if file_path.endswith(".csv"):
        items = exporter.import_from_csv(file_path)
    else:
        items = exporter.import_from_json(file_path)

    db = Database()
    added_count = 0
    for item in items:
        if not db.get_product_by_url(item.url):
            db.add_product(item)
            added_count += 1

    console.print(f"[bold green]Successfully imported {added_count} new products.[/bold green]")


@main.command(name="watch")
@click.option("--interval", "-i", default=DEFAULT_CHECK_INTERVAL_SECONDS, help="Check interval in seconds")
@click.option("--tag", default=None, help="Filter by tag")
def watch_command(interval: int, tag: str | None) -> None:
    db = Database()
    tracker = PriceTracker(db=db)
    console.print(f"[bold cyan]Starting Price Tracker Watcher (Interval: {interval}s)...[/bold cyan]")
    console.print("[dim]Press Ctrl+C to stop.[/dim]\n")

    try:
        while True:
            console.print(f"[{time.strftime('%X')}] Checking prices...")
            results = tracker.check_all(tag=tag)
            for prod, alerts, err in results:
                if err:
                    console.print(f"  [red]Error #{prod.id} ({prod.name}): {err}[/red]")
                else:
                    console.print(f"  [green]#{prod.id} {prod.name}:[/green] {prod.currency} {prod.current_price:.2f}")
                    for a in alerts:
                        console.print(f"    └─ [bold yellow]{a.alert_type}:[/bold yellow] {a.message}")
            time.sleep(interval)
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Watcher stopped by user.[/bold yellow]")


if __name__ == "__main__":
    main()
