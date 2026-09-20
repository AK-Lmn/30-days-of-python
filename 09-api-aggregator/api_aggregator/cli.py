import asyncio
import csv
import json
from pathlib import Path
import time
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from api_aggregator.config import CONFIG
from api_aggregator.engine import AggregationEngine


import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

console = Console(legacy_windows=False)


@click.group()
def main() -> None:
    pass


@main.command()
@click.option("--host", default=CONFIG.default_host, help="Host to bind server to.")
@click.option("--port", default=CONFIG.default_port, type=int, help="Port to bind server to.")
@click.option("--reload", is_flag=True, default=False, help="Enable auto-reload.")
def serve(host: str, port: int, reload: bool) -> None:
    import uvicorn

    console.print(
        Panel.fit(
            f"[bold green]Starting {CONFIG.app_name} v{CONFIG.app_version}[/bold green]\n"
            f"[cyan]Listening on:[/cyan] http://{host}:{port}\n"
            f"[cyan]OpenAPI Docs:[/cyan] http://{host}:{port}/docs",
            border_style="green",
        )
    )
    uvicorn.run("api_aggregator.server:app", host=host, port=port, reload=reload)


@main.command()
@click.option("--limit", default=5, type=int, help="Number of items to fetch.")
@click.option("--no-cache", is_flag=True, default=False, help="Bypass cache.")
@click.option("--mock", is_flag=True, default=False, help="Force mock data.")
def news(limit: int, no_cache: bool, mock: bool) -> None:
    async def run() -> None:
        engine = AggregationEngine()
        try:
            with console.status("[bold cyan]Aggregating tech news from multiple providers..."):
                envelope = await engine.aggregate_news(
                    limit=limit, use_cache=not no_cache, force_mock=mock
                )

            table = Table(
                title=f"Aggregated News ({envelope.count} items, {envelope.latency_ms}ms, cached={envelope.cached})",
                show_lines=True,
            )
            table.add_column("Source", style="cyan", width=12)
            table.add_column("Title", style="bold white")
            table.add_column("Author", style="magenta", width=15)
            table.add_column("Score", justify="right", style="green", width=8)
            table.add_column("Comments", justify="right", style="yellow", width=10)

            for item in envelope.data:
                table.add_row(
                    item.source,
                    item.title,
                    item.author,
                    str(item.score),
                    str(item.comments_count),
                )

            console.print(table)
            console.print(
                f"[dim]Sources Queried: {', '.join(envelope.sources_queried)} | Succeeded: {', '.join(envelope.sources_succeeded)}[/dim]"
            )
        finally:
            await engine.close()

    asyncio.run(run())


@main.command()
@click.option("--coins", default="BTC,ETH,SOL", help="Comma-separated coin symbols.")
@click.option("--no-cache", is_flag=True, default=False, help="Bypass cache.")
@click.option("--mock", is_flag=True, default=False, help="Force mock data.")
def crypto(coins: str, no_cache: bool, mock: bool) -> None:
    async def run() -> None:
        engine = AggregationEngine()
        try:
            symbols = [s.strip().upper() for s in coins.split(",") if s.strip()]
            with console.status("[bold yellow]Aggregating crypto exchange rates..."):
                envelope = await engine.aggregate_crypto(
                    symbols=symbols, use_cache=not no_cache, force_mock=mock
                )

            table = Table(
                title=f"Reconciled Crypto Rates ({envelope.latency_ms}ms, cached={envelope.cached})",
                show_lines=True,
            )
            table.add_column("Symbol", style="bold cyan", width=8)
            table.add_column("Name", style="white", width=12)
            table.add_column("Avg Price (USD)", justify="right", style="bold green", width=16)
            table.add_column("24h Change", justify="right", width=12)
            table.add_column("Spread", justify="right", style="yellow", width=10)
            table.add_column("Contributing Sources", style="magenta")

            for rate in envelope.data:
                change_style = "green" if rate.change_24h_percent >= 0 else "red"
                change_str = f"[{change_style}]{rate.change_24h_percent:+.2f}%[/{change_style}]"
                table.add_row(
                    rate.symbol,
                    rate.name,
                    f"${rate.price_usd:,.2f}",
                    change_str,
                    f"{rate.discrepancy_percent:.2f}%",
                    ", ".join(rate.sources),
                )

            console.print(table)
        finally:
            await engine.close()

    asyncio.run(run())


@main.command()
@click.option("--city", default="London", help="City name.")
@click.option("--no-cache", is_flag=True, default=False, help="Bypass cache.")
@click.option("--mock", is_flag=True, default=False, help="Force mock data.")
def weather(city: str, no_cache: bool, mock: bool) -> None:
    async def run() -> None:
        engine = AggregationEngine()
        try:
            with console.status(f"[bold blue]Fetching weather for {city}..."):
                envelope = await engine.aggregate_weather(
                    city=city, use_cache=not no_cache, force_mock=mock
                )

            report = envelope.data
            if not report:
                console.print(f"[red]Could not retrieve weather data for {city}.[/red]")
                return

            panel_text = (
                f"[bold white]Location:[/bold white] {report.location}\n"
                f"[bold white]Coordinates:[/bold white] {report.latitude:.4f}, {report.longitude:.4f}\n"
                f"[bold white]Condition:[/bold white] [cyan]{report.condition}[/cyan]\n"
                f"[bold white]Temperature:[/bold white] [bold green]{report.temperature_c}°C[/bold green] ({report.temperature_f}°F)\n"
                f"[bold white]Humidity:[/bold white] {report.humidity_percent}%\n"
                f"[bold white]Wind Speed:[/bold white] {report.wind_speed_kmh} km/h\n"
                f"[bold white]Sources:[/bold white] {', '.join(report.sources)}\n"
                f"[dim]Latency: {envelope.latency_ms}ms | Cached: {envelope.cached}[/dim]"
            )
            console.print(Panel(panel_text, title=f"Weather — {report.location}", border_style="blue"))
        finally:
            await engine.close()

    asyncio.run(run())


@main.command()
@click.option("--no-cache", is_flag=True, default=False, help="Bypass cache.")
@click.option("--mock", is_flag=True, default=False, help="Force mock data.")
def overview(no_cache: bool, mock: bool) -> None:
    async def run() -> None:
        engine = AggregationEngine()
        try:
            with console.status("[bold green]Generating multi-domain aggregated overview..."):
                envelope = await engine.aggregate_overview(
                    use_cache=not no_cache, force_mock=mock
                )

            data = envelope.data
            console.print(
                Panel.fit(
                    f"[bold green]Aggregated Executive Snapshot[/bold green]\n"
                    f"[dim]Timestamp: {data.timestamp} | Latency: {envelope.latency_ms}ms | Cached: {envelope.cached}[/dim]",
                    border_style="green",
                )
            )

            if data.weather:
                console.print(
                    f"[bold blue]Weather ({data.weather.location}):[/bold blue] "
                    f"{data.weather.temperature_c}°C, {data.weather.condition}, Wind {data.weather.wind_speed_kmh} km/h"
                )

            if data.crypto_rates:
                crypto_line = " | ".join(
                    f"[bold]{r.symbol}:[/bold] ${r.price_usd:,.2f} ({r.change_24h_percent:+.2f}%)"
                    for r in data.crypto_rates
                )
                console.print(f"[bold yellow]Crypto Rates:[/bold yellow] {crypto_line}\n")

            if data.top_news:
                console.print("[bold cyan]Top Headlines:[/bold cyan]")
                for idx, item in enumerate(data.top_news, 1):
                    console.print(f" {idx}. [{item.source}] {item.title} ([dim]{item.url}[/dim])")
        finally:
            await engine.close()

    asyncio.run(run())


@main.command()
def status() -> None:
    async def run() -> None:
        engine = AggregationEngine()
        try:
            health_map = engine.get_provider_health_map()
            cache_stats = await engine.cache.get_stats()

            table = Table(title="Provider Health & Circuit Status", show_lines=True)
            table.add_column("Provider", style="bold cyan")
            table.add_column("Domain", style="white")
            table.add_column("Circuit State", style="bold")
            table.add_column("Latency (ms)", justify="right")
            table.add_column("Successes", justify="right", style="green")
            table.add_column("Failures", justify="right", style="red")

            for name, h in health_map.items():
                c_val = getattr(h.circuit_state, "value", str(h.circuit_state))
                c_style = (
                    "green"
                    if c_val == "CLOSED"
                    else ("yellow" if c_val == "HALF_OPEN" else "red")
                )
                table.add_row(
                    name,
                    h.domain,
                    f"[{c_style}]{c_val}[/{c_style}]",
                    str(h.last_latency_ms),
                    str(h.success_count),
                    str(h.error_count),
                )

            console.print(table)

            cache_panel = (
                f"Entries: {cache_stats['size']} / {cache_stats['max_size']}\n"
                f"Hits: {cache_stats['hits']} | Misses: {cache_stats['misses']}\n"
                f"Hit Ratio: {cache_stats['hit_ratio'] * 100:.1f}%\n"
                f"Evictions: {cache_stats['evictions']}"
            )
            console.print(Panel(cache_panel, title="Cache Telemetry", border_style="cyan"))
        finally:
            await engine.close()

    asyncio.run(run())


@main.command()
@click.option("--iterations", default=3, type=int, help="Benchmark run count.")
def benchmark(iterations: int) -> None:
    async def run() -> None:
        engine = AggregationEngine()
        try:
            console.print(f"[bold cyan]Running {iterations} benchmark iterations...[/bold cyan]")

            parallel_times: list[float] = []
            for _ in range(iterations):
                start = time.perf_counter()
                await engine.aggregate_overview(use_cache=False, force_mock=True)
                parallel_times.append((time.perf_counter() - start) * 1000.0)

            sequential_times: list[float] = []
            for _ in range(iterations):
                start = time.perf_counter()
                await engine.aggregate_news(limit=5, use_cache=False, force_mock=True)
                await engine.aggregate_crypto(use_cache=False, force_mock=True)
                await engine.aggregate_weather(use_cache=False, force_mock=True)
                sequential_times.append((time.perf_counter() - start) * 1000.0)

            avg_par = sum(parallel_times) / len(parallel_times)
            avg_seq = sum(sequential_times) / len(sequential_times)
            speedup = (avg_seq / avg_par) if avg_par > 0 else 1.0

            table = Table(title="Aggregation Concurrency Benchmark", show_lines=True)
            table.add_column("Execution Mode", style="bold")
            table.add_column("Min (ms)", justify="right")
            table.add_column("Avg (ms)", justify="right", style="green")
            table.add_column("Max (ms)", justify="right")

            table.add_row(
                "Parallel (Asyncio Gather)",
                f"{min(parallel_times):.2f}",
                f"{avg_par:.2f}",
                f"{max(parallel_times):.2f}",
            )
            table.add_row(
                "Sequential (Synchronous Fanout)",
                f"{min(sequential_times):.2f}",
                f"{avg_seq:.2f}",
                f"{max(sequential_times):.2f}",
            )
            console.print(table)
            console.print(f"[bold green]Speedup Factor:[/bold green] [bold cyan]{speedup:.2f}x[/bold cyan]")
        finally:
            await engine.close()

    asyncio.run(run())


@main.command()
@click.option(
    "--domain",
    type=click.Choice(["news", "crypto", "weather", "overview"]),
    required=True,
    help="Domain to export.",
)
@click.option(
    "--format",
    "export_format",
    type=click.Choice(["json", "csv"]),
    default="json",
    help="Export file format.",
)
@click.option("--output", required=True, help="Destination file path.")
def export(domain: str, export_format: str, output: str) -> None:
    async def run() -> None:
        engine = AggregationEngine()
        try:
            out_path = Path(output)
            out_path.parent.mkdir(parents=True, exist_ok=True)

            if domain == "news":
                res = await engine.aggregate_news(limit=20, force_mock=True)
                data = [item.model_dump() for item in res.data]
            elif domain == "crypto":
                res = await engine.aggregate_crypto(
                    symbols=["BTC", "ETH", "SOL", "ADA", "DOGE"], force_mock=True
                )
                data = [rate.model_dump() for rate in res.data]
            elif domain == "weather":
                res = await engine.aggregate_weather(city="London", force_mock=True)
                data = [res.data.model_dump()] if res.data else []
            else:
                res = await engine.aggregate_overview(force_mock=True)
                data = [res.data.model_dump()]

            if export_format == "json":
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            else:
                if data:
                    keys = list(data[0].keys())
                    with open(out_path, "w", newline="", encoding="utf-8") as f:
                        writer = csv.DictWriter(f, fieldnames=keys)
                        writer.writeheader()
                        for row in data:
                            cleaned = {
                                k: (
                                    ", ".join(v)
                                    if isinstance(v, list)
                                    else (
                                        json.dumps(v)
                                        if isinstance(v, dict)
                                        else v
                                    )
                                )
                                for k, v in row.items()
                            }
                            writer.writerow(cleaned)

            console.print(
                f"[bold green]Successfully exported {len(data)} items to {out_path}[/bold green]"
            )
        finally:
            await engine.close()

    asyncio.run(run())


@main.command()
def gui() -> None:
    from api_aggregator.gui import run_gui

    run_gui()


if __name__ == "__main__":
    main()
