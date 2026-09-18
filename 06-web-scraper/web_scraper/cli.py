import json
from pathlib import Path
import sys
import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table
from web_scraper.cache import ResponseCache
from web_scraper.client import HttpClient
from web_scraper.config import get_output_dir
from web_scraper.engine import ScraperEngine
from web_scraper.exporter import DataExporter
from web_scraper.models import ItemRule, PaginationConfig, ScrapeJob
from web_scraper.parser import HtmlParser
from web_scraper.presets import get_preset, list_presets
from web_scraper.robots import RobotsChecker

console = Console()


def parse_field_argument(field_str: str) -> ItemRule:
    parts = field_str.split(":")
    name = parts[0].strip()
    selector = parts[1].strip() if len(parts) > 1 else ""
    extract = parts[2].strip() if len(parts) > 2 else "text"
    cast = parts[3].strip() if len(parts) > 3 else "str"
    attr_name = None

    if extract.startswith("attr(") and extract.endswith(")"):
        attr_name = extract[5:-1]
        extract = "attr"
    elif extract not in ("text", "html", "href", "src", "attr"):
        attr_name = extract
        extract = "attr"

    return ItemRule(
        name=name,
        selector=selector,
        extract=extract,
        attr_name=attr_name,
        cast=cast,
    )


@click.group()
def main() -> None:
    pass


@main.command(name="run")
@click.argument("url")
@click.option("-c", "--container", help="CSS selector for list item containers.")
@click.option(
    "-f",
    "--field",
    "fields",
    multiple=True,
    help="Field rule in format 'name:selector[:extract[:cast]]'.",
)
@click.option(
    "--strategy",
    type=click.Choice(["none", "next_link", "page_param", "offset"]),
    default="none",
    help="Pagination strategy.",
)
@click.option("-n", "--next-selector", help="CSS selector for next page link.")
@click.option("--page-param", default="page", help="Query parameter name for page number.")
@click.option("-p", "--pages", default=1, type=int, help="Maximum number of pages to scrape.")
@click.option("-m", "--max-items", type=int, default=None, help="Maximum total items to scrape.")
@click.option("-d", "--delay", default=0.5, type=float, help="Delay in seconds between requests.")
@click.option("-r", "--retries", default=3, type=int, help="Maximum retries for failed requests.")
@click.option("-t", "--timeout", default=20.0, type=float, help="HTTP request timeout in seconds.")
@click.option("--no-robots", is_flag=True, default=False, help="Disable robots.txt compliance.")
@click.option("--cache/--no-cache", default=False, help="Enable or disable HTTP disk caching.")
@click.option("-o", "--export", help="Output file path (e.g. data.json, data.csv, data.db).")
def run_command(
    url: str,
    container: str | None,
    fields: tuple[str, ...],
    strategy: str,
    next_selector: str | None,
    page_param: str,
    pages: int,
    max_items: int | None,
    delay: float,
    retries: int,
    timeout: float,
    no_robots: bool,
    cache: bool,
    export: str | None,
) -> None:
    rules: list[ItemRule] = []
    for field_arg in fields:
        rules.append(parse_field_argument(field_arg))

    pagination_config = PaginationConfig(
        strategy=strategy,
        next_selector=next_selector,
        page_param=page_param,
        max_pages=pages,
        max_items=max_items,
    )

    job = ScrapeJob(
        url=url,
        container_selector=container,
        rules=rules,
        pagination=pagination_config,
        timeout=timeout,
        max_retries=retries,
        rate_limit_delay=delay,
        respect_robots_txt=not no_robots,
        use_cache=cache,
    )

    console.print(
        Panel(
            f"[bold cyan]URL:[/bold cyan] {url}\n"
            f"[bold cyan]Container:[/bold cyan] {container or '(single item)'}\n"
            f"[bold cyan]Fields:[/bold cyan] {', '.join(r.name for r in rules) or '(none)'}\n"
            f"[bold cyan]Pagination:[/bold cyan] {strategy} (max {pages} pages)",
            title="[bold green]Web Scraper Engine[/bold green]",
            expand=False,
        )
    )

    engine = ScraperEngine()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[yellow]Scraping...", total=pages)

        def on_progress(pg: int, item_cnt: int, curr_url: str) -> None:
            progress.update(
                task,
                completed=pg,
                description=f"[green]Page {pg}/{pages} ({item_cnt} items scraped)[/green]",
            )

        result = engine.run(job, progress_callback=on_progress)

    if result.errors:
        for err in result.errors:
            console.print(f"[bold red]Error:[/bold red] {err}")

    console.print(
        f"[bold]Completed in {result.duration_seconds:.2f}s — Scraped {result.total_items} items across {result.total_pages} page(s).[/bold]"
    )

    if result.items:
        preview_table = Table(title="Scraped Items Preview")
        keys = list(result.items[0].keys())
        for key in keys:
            preview_table.add_column(key, style="cyan")

        for item in result.items[:5]:
            preview_table.add_row(*[str(item.get(k, ""))[:60] for k in keys])

        console.print(preview_table)

    if export:
        export_path = Path(export)
        DataExporter.export_by_format(result.items, export_path)
        console.print(f"[bold green]Data exported to:[/bold green] {export_path.resolve()}")
    elif result.items:
        auto_file = get_output_dir() / "scraped_results.json"
        DataExporter.export_json(result.items, auto_file)
        console.print(f"[dim]Results automatically saved to {auto_file}[/dim]")


@main.group(name="preset")
def preset_group() -> None:
    pass


@preset_group.command(name="list")
def preset_list() -> None:
    table = Table(title="Available Scraper Presets")
    table.add_column("Name", style="bold green")
    table.add_column("Target URL", style="cyan")
    table.add_column("Fields", style="magenta")

    for name in list_presets():
        job = get_preset(name)
        if job:
            fields_str = ", ".join(r.name for r in job.rules)
            table.add_row(name, job.url, fields_str)

    console.print(table)


@preset_group.command(name="run")
@click.argument("name")
@click.option("--url", help="Override preset URL.")
@click.option("-p", "--pages", type=int, help="Override preset max pages.")
@click.option("-m", "--max-items", type=int, help="Override preset max items.")
@click.option("-d", "--delay", type=float, help="Override request delay.")
@click.option("--no-robots", is_flag=True, default=False, help="Disable robots.txt check.")
@click.option("--cache/--no-cache", default=False, help="Enable or disable cache.")
@click.option("-o", "--export", help="Output file path (JSON, CSV, Markdown, SQLite).")
def preset_run(
    name: str,
    url: str | None,
    pages: int | None,
    max_items: int | None,
    delay: float | None,
    no_robots: bool,
    cache: bool,
    export: str | None,
) -> None:
    job = get_preset(name)
    if job is None:
        console.print(f"[bold red]Preset '{name}' not found. Run 'scraper preset list' to view options.[/bold red]")
        sys.exit(1)

    if url:
        job.url = url
    if pages is not None:
        job.pagination.max_pages = pages
    if max_items is not None:
        job.pagination.max_items = max_items
    if delay is not None:
        job.rate_limit_delay = delay
    if no_robots:
        job.respect_robots_txt = False
    job.use_cache = cache

    console.print(Panel(f"[bold green]Running Preset:[/bold green] {name}\n[cyan]URL:[/cyan] {job.url}"))
    engine = ScraperEngine()
    result = engine.run(job)

    if result.errors:
        for err in result.errors:
            console.print(f"[bold red]Error:[/bold red] {err}")

    console.print(
        f"[bold]Done! Scraped {result.total_items} items from {result.total_pages} page(s) in {result.duration_seconds:.2f}s.[/bold]"
    )

    if result.items:
        table = Table(title=f"Results Preview ({name})")
        keys = list(result.items[0].keys())
        for key in keys:
            table.add_column(key, style="cyan")
        for item in result.items[:5]:
            table.add_row(*[str(item.get(k, ""))[:60] for k in keys])
        console.print(table)

    if export:
        out_path = Path(export)
        DataExporter.export_by_format(result.items, out_path)
        console.print(f"[bold green]Exported to:[/bold green] {out_path.resolve()}")


@main.command(name="test-selector")
@click.argument("url")
@click.argument("selector")
@click.option("-l", "--limit", default=5, type=int, help="Limit number of matched elements.")
def test_selector(url: str, selector: str, limit: int) -> None:
    console.print(f"[bold]Fetching {url} to test selector:[/bold] [yellow]{selector}[/yellow]")
    client = HttpClient()
    response = client.fetch(url)

    if not response.is_success:
        console.print(f"[bold red]Failed to fetch URL:[/bold red] HTTP {response.status_code}")
        return

    parser = HtmlParser()
    matches = parser.query_selector(response.html, selector, limit=limit)

    if not matches:
        console.print(f"[yellow]No elements matched selector '{selector}'.[/yellow]")
        return

    console.print(f"[bold green]Found {len(matches)} matching element(s) (displaying up to {limit}):[/bold green]")
    table = Table()
    table.add_column("#", style="dim", width=4)
    table.add_column("Tag", style="bold magenta", width=8)
    table.add_column("Text Content", style="cyan")
    table.add_column("Attributes", style="green")

    for i, match in enumerate(matches, 1):
        attrs_str = json.dumps(match["attributes"], ensure_ascii=False)
        table.add_row(str(i), match["tag"], match["text"], attrs_str)

    console.print(table)


@main.command(name="robots")
@click.argument("url")
@click.option("-u", "--user-agent", default="WebScraperEngine", help="User agent to verify.")
def check_robots(url: str, user_agent: str) -> None:
    checker = RobotsChecker()
    allowed = checker.can_fetch(url, user_agent)
    crawl_delay = checker.get_crawl_delay(url, user_agent)

    status_str = "[bold green]ALLOWED[/bold green]" if allowed else "[bold red]DISALLOWED[/bold red]"
    console.print(f"URL: {url}")
    console.print(f"User Agent: {user_agent}")
    console.print(f"Robots.txt Status: {status_str}")
    if crawl_delay is not None:
        console.print(f"Crawl Delay: {crawl_delay}s")


@main.group(name="cache")
def cache_group() -> None:
    pass


@cache_group.command(name="clear")
def cache_clear() -> None:
    cache = ResponseCache()
    removed = cache.clear()
    console.print(f"[bold green]Cleared {removed} cached responses.[/bold green]")


@cache_group.command(name="stats")
def cache_stats() -> None:
    cache = ResponseCache()
    count = cache.count()
    console.print(f"[cyan]Cached responses on disk:[/cyan] {count} files in {cache.cache_dir}")


if __name__ == "__main__":
    main()
