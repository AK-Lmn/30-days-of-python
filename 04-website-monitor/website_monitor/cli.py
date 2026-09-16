from datetime import datetime, timezone
from pathlib import Path
import sys
import time
from typing import List, Optional

import click
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from website_monitor.checker import check_target
from website_monitor.config import (
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_CHECK_INTERVAL_SECONDS,
    DEFAULT_RETENTION_DAYS,
)
from website_monitor.db import (
    add_target,
    delete_target,
    get_all_target_stats,
    get_recent_checks,
    get_target,
    get_target_by_url,
    get_target_stats,
    init_db,
    list_incidents,
    list_targets,
    prune_logs,
)
from website_monitor.engine import MonitorEngine
from website_monitor.exporter import export_to_csv, export_to_json, export_to_markdown, save_export
from website_monitor.models import CheckResult, MonitorTarget


if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console()


@click.group()
def main() -> None:
    init_db()


@main.group()
def target() -> None:
    pass


@target.command("add")
@click.argument("url")
@click.option("--name", "-n", help="Human-readable label for target")
@click.option("--method", "-m", default="GET", help="HTTP method (GET, POST, etc.)")
@click.option("--expected-status", "-s", default=200, type=int, help="Expected HTTP response status")
@click.option("--keyword", "-k", help="Required substring in response body")
@click.option("--timeout", "-t", default=DEFAULT_TIMEOUT_SECONDS, type=float, help="Timeout in seconds")
@click.option("--interval", "-i", default=DEFAULT_CHECK_INTERVAL_SECONDS, type=int, help="Check interval in seconds")
@click.option("--header", "-H", multiple=True, help="Header in format 'Key: Value'")
@click.option("--tag", multiple=True, help="Tag for grouping")
def target_add(
    url: str,
    name: Optional[str],
    method: str,
    expected_status: int,
    keyword: Optional[str],
    timeout: float,
    interval: int,
    header: tuple,
    tag: tuple,
) -> None:
    headers_dict = {}
    for h in header:
        if ":" in h:
            k, v = h.split(":", 1)
            headers_dict[k.strip()] = v.strip()

    target_obj = MonitorTarget(
        url=url,
        name=name or url,
        method=method,
        expected_status=expected_status,
        keyword=keyword,
        timeout_seconds=timeout,
        check_interval_seconds=interval,
        headers=headers_dict,
        tags=list(tag),
    )

    try:
        saved = add_target(target_obj)
        console.print(f"[bold green]Target added successfully! [ID: {saved.id}][/bold green] {saved.name} ({saved.url})")
    except Exception as e:
        console.print(f"[bold red]Failed to add target:[/bold red] {e}")


@target.command("list")
@click.option("--active-only", is_flag=True, help="Show only active targets")
@click.option("--tag", help="Filter by tag")
def target_list(active_only: bool, tag: Optional[str]) -> None:
    targets = list_targets(active_only=active_only, tag=tag)
    if not targets:
        console.print("[yellow]No targets configured. Add one with: web-monitor target add <url>[/yellow]")
        return

    table = Table(title="Configured Monitor Targets", header_style="bold cyan")
    table.add_column("ID", justify="right", style="dim")
    table.add_column("Name", style="bold")
    table.add_column("URL")
    table.add_column("Method", justify="center")
    table.add_column("Expected", justify="center")
    table.add_column("Timeout", justify="right")
    table.add_column("Tags")
    table.add_column("Active", justify="center")

    for t in targets:
        active_str = "[green]Yes[/green]" if t.is_active else "[dim red]No[/dim red]"
        tags_str = ", ".join(t.tags) if t.tags else "N/A"
        table.add_row(
            str(t.id),
            t.name,
            t.url,
            t.method,
            str(t.expected_status),
            f"{t.timeout_seconds}s",
            tags_str,
            active_str,
        )

    console.print(table)


@target.command("remove")
@click.argument("target_id", type=int)
def target_remove(target_id: int) -> None:
    target_obj = get_target(target_id)
    if not target_obj:
        console.print(f"[bold red]Target #{target_id} not found.[/bold red]")
        return

    success = delete_target(target_id)
    if success:
        console.print(f"[green]Removed target #{target_id}: {target_obj.name}[/green]")
    else:
        console.print(f"[red]Failed to remove target #{target_id}[/red]")


@main.command("check")
@click.argument("target_identifier", required=False)
@click.option("--tag", help="Filter targets by tag")
def check(target_identifier: Optional[str], tag: Optional[str]) -> None:
    engine = MonitorEngine()

    if target_identifier:
        target_obj = None
        if target_identifier.isdigit():
            target_obj = get_target(int(target_identifier))
        if not target_obj:
            target_obj = get_target_by_url(target_identifier)
        if not target_obj:
            console.print(f"[bold red]Target '{target_identifier}' not found in database.[/bold red]")
            return

        result = engine.check_target_sync(target_obj)
        status_text = "[bold green]UP[/bold green]" if result.is_up else "[bold red]DOWN[/bold red]"
        console.print(
            f"{status_text} | {target_obj.name} ({target_obj.url}) | "
            f"Status: {result.status_code or 'ERR'} | {result.response_time_ms:.1f}ms"
        )
        if result.ssl_days_left is not None:
            console.print(f"  SSL Certificate: {result.ssl_days_left} days remaining")
        if result.error_message:
            console.print(f"  [red]Error: {result.error_message}[/red]")
        return

    targets = list_targets(active_only=True, tag=tag)
    if not targets:
        console.print("[yellow]No active targets found to check.[/yellow]")
        return

    console.print(f"Checking {len(targets)} active targets...\n")
    table = Table(title="Health Check Results", header_style="bold blue")
    table.add_column("Status", justify="center")
    table.add_column("Name", style="bold")
    table.add_column("HTTP Code", justify="center")
    table.add_column("Latency", justify="right")
    table.add_column("SSL Expiry", justify="right")
    table.add_column("Details")

    for t in targets:
        res = engine.check_target_sync(t)
        status_badge = "[green]UP[/green]" if res.is_up else "[red]DOWN[/red]"
        code_str = str(res.status_code) if res.status_code is not None else "[red]ERR[/red]"
        latency_str = f"{res.response_time_ms:.1f} ms"
        ssl_str = f"{res.ssl_days_left} days" if res.ssl_days_left is not None else "N/A"
        details_str = res.error_message or "OK"

        table.add_row(
            status_badge,
            t.name,
            code_str,
            latency_str,
            ssl_str,
            details_str if res.is_up else f"[red]{details_str}[/red]",
        )

    console.print(table)


@main.command("stats")
@click.argument("target_id", type=int, required=False)
@click.option("--hours", default=24, type=int, help="Time window in hours")
def stats(target_id: Optional[int], hours: int) -> None:
    if target_id is not None:
        target_stat = get_target_stats(target_id, hours=hours)
        if not target_stat:
            console.print(f"[bold red]Target #{target_id} not found.[/bold red]")
            return

        table = Table(title=f"Statistics for {target_stat.target_name} (Past {hours}h)")
        table.add_column("Metric", style="bold cyan")
        table.add_column("Value")

        uptime_color = "green" if target_stat.uptime_percentage >= 99.0 else "yellow"
        table.add_row("URL", target_stat.target_url)
        table.add_row("Uptime %", f"[{uptime_color}]{target_stat.uptime_percentage:.2f}%[/{uptime_color}]")
        table.add_row("Total Checks", str(target_stat.total_checks))
        table.add_row("Up Checks", str(target_stat.up_checks))
        table.add_row("Down Checks", str(target_stat.down_checks))
        table.add_row("Avg Latency", f"{target_stat.avg_latency_ms:.1f} ms")
        table.add_row("p95 Latency", f"{target_stat.p95_latency_ms:.1f} ms")
        table.add_row("Min / Max Latency", f"{target_stat.min_latency_ms:.1f} ms / {target_stat.max_latency_ms:.1f} ms")
        table.add_row("Active Outage", "[red]YES[/red]" if target_stat.active_incident else "[green]None[/green]")
        if target_stat.ssl_days_left is not None:
            table.add_row("SSL Days Left", f"{target_stat.ssl_days_left} days")

        console.print(table)
        return

    all_stats = get_all_target_stats(hours=hours)
    if not all_stats:
        console.print("[yellow]No targets found.[/yellow]")
        return

    table = Table(title=f"Global Availability & SLA Overview (Past {hours}h)", header_style="bold cyan")
    table.add_column("Target", style="bold")
    table.add_column("Status", justify="center")
    table.add_column("Uptime %", justify="right")
    table.add_column("Avg Latency", justify="right")
    table.add_column("p95 Latency", justify="right")
    table.add_column("Checks", justify="right")
    table.add_column("Outage", justify="center")

    for s in all_stats:
        status_str = "[green]UP[/green]" if s.last_is_up is True else ("[red]DOWN[/red]" if s.last_is_up is False else "N/A")
        uptime_color = "green" if s.uptime_percentage >= 99.0 else ("yellow" if s.uptime_percentage >= 95.0 else "red")
        table.add_row(
            s.target_name,
            status_str,
            f"[{uptime_color}]{s.uptime_percentage:.2f}%[/{uptime_color}]",
            f"{s.avg_latency_ms:.1f} ms",
            f"{s.p95_latency_ms:.1f} ms",
            str(s.total_checks),
            "[red][OUTAGE][/red]" if s.active_incident else "[green]None[/green]",
        )

    console.print(table)


@main.command("watch")
@click.option("--interval", "-i", default=30, type=int, help="Polling interval in seconds")
@click.option("--tag", help="Filter by tag")
def watch(interval: int, tag: Optional[str]) -> None:
    engine = MonitorEngine()
    console.print(f"[bold blue]Starting continuous website monitor (Interval: {interval}s). Press Ctrl+C to exit.[/bold blue]\n")

    def on_check(t: MonitorTarget, r: CheckResult) -> None:
        now_str = datetime.now().strftime("%H:%M:%S")
        status_text = "[green]UP[/green]" if r.is_up else "[red]DOWN[/red]"
        code_str = str(r.status_code) if r.status_code is not None else "ERR"
        line = f"[{now_str}] [{status_text}] {t.name} ({t.url}) - Status: {code_str} - {r.response_time_ms:.1f}ms"
        if not r.is_up and r.error_message:
            line += f" - [red]{r.error_message}[/red]"
        console.print(line)

    try:
        engine.start_loop(interval_seconds=interval, tag=tag, callback=on_check)
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoring stopped by user.[/yellow]")


@main.command("dashboard")
@click.option("--interval", "-i", default=10, type=int, help="Refresh interval in seconds")
def dashboard(interval: int) -> None:
    engine = MonitorEngine()

    def generate_layout() -> Table:
        main_table = Table.grid(padding=1)
        stats_list = get_all_target_stats(hours=24)
        recent_logs = get_recent_checks(limit=10)

        total_targets = len(stats_list)
        up_targets = sum(1 for s in stats_list if s.last_is_up is True)
        down_targets = sum(1 for s in stats_list if s.last_is_up is False)
        avg_overall_latency = (
            sum(s.avg_latency_ms for s in stats_list) / total_targets if total_targets > 0 else 0.0
        )

        header_text = Text()
        header_text.append("WEBSITE MONITOR LIVE DASHBOARD\n", style="bold white on blue")
        header_text.append(
            f"Targets: {total_targets} | Up: {up_targets} | Down: {down_targets} | Avg Latency: {avg_overall_latency:.1f} ms"
        )
        main_table.add_row(Panel(header_text, style="blue"))

        target_table = Table(title="Live Monitored Endpoints", header_style="bold cyan", expand=True)
        target_table.add_column("Status", justify="center")
        target_table.add_column("Name", style="bold")
        target_table.add_column("URL")
        target_table.add_column("Code", justify="center")
        target_table.add_column("Latency", justify="right")
        target_table.add_column("Uptime (24h)", justify="right")

        for s in stats_list:
            status_dot = "[green]UP[/green]" if s.last_is_up is True else ("[red]DOWN[/red]" if s.last_is_up is False else "-")
            code_str = str(s.last_status_code) if s.last_status_code is not None else "-"
            latency_str = f"{s.last_latency_ms:.1f} ms" if s.last_latency_ms is not None else "-"
            uptime_color = "green" if s.uptime_percentage >= 99.0 else "yellow"
            target_table.add_row(
                status_dot,
                s.target_name,
                s.target_url,
                code_str,
                latency_str,
                f"[{uptime_color}]{s.uptime_percentage:.1f}%[/{uptime_color}]",
            )
        main_table.add_row(target_table)

        log_table = Table(title="Recent Activity Feed", header_style="bold magenta", expand=True)
        log_table.add_column("Timestamp", style="dim")
        log_table.add_column("Target")
        log_table.add_column("Status", justify="center")
        log_table.add_column("Latency", justify="right")
        log_table.add_column("Message")

        for log in recent_logs:
            st = "[green]UP[/green]" if log.is_up else "[red]DOWN[/red]"
            log_table.add_row(
                log.checked_at.split("T")[-1][:8] if "T" in log.checked_at else log.checked_at,
                log.target_name or str(log.target_id),
                st,
                f"{log.response_time_ms:.1f} ms",
                log.error_message or "OK",
            )
        main_table.add_row(log_table)
        return main_table

    with Live(generate_layout(), refresh_per_second=1, console=console) as live:
        try:
            while True:
                engine.check_all()
                live.update(generate_layout())
                time.sleep(interval)
        except KeyboardInterrupt:
            pass


@main.command("incidents")
@click.option("--unresolved", "-u", is_flag=True, help="Show only ongoing unresolved incidents")
@click.option("--limit", "-l", default=25, type=int, help="Maximum incidents to display")
def incidents(unresolved: bool, limit: int) -> None:
    inc_list = list_incidents(unresolved_only=unresolved, limit=limit)
    if not inc_list:
        console.print("[green]No incidents recorded! All systems operational.[/green]")
        return

    table = Table(title="Incidents & Outage Log", header_style="bold red")
    table.add_column("ID", justify="right", style="dim")
    table.add_column("Target", style="bold")
    table.add_column("Started At")
    table.add_column("Duration", justify="right")
    table.add_column("Status", justify="center")
    table.add_column("Root Cause")

    for inc in inc_list:
        duration_str = f"{int(inc.duration_seconds)}s" if inc.duration_seconds is not None else "[bold red]Active[/bold red]"
        status_badge = "[green]Resolved[/green]" if inc.resolved else "[red][OUTAGE][/red]"
        table.add_row(
            str(inc.id),
            inc.target_name or f"Target #{inc.target_id}",
            inc.started_at,
            duration_str,
            status_badge,
            inc.reason,
        )

    console.print(table)


@main.command("export")
@click.option("--format", "-f", "export_format", type=click.Choice(["json", "csv", "md"]), default="md")
@click.option("--output", "-o", "output_path", type=click.Path(path_type=Path), help="File path to save output")
def export(export_format: str, output_path: Optional[Path]) -> None:
    stats_list = get_all_target_stats(hours=24)
    inc_list = list_incidents(limit=50)

    if export_format == "json":
        content = export_to_json(stats_list, inc_list)
    elif export_format == "csv":
        content = export_to_csv(stats_list)
    else:
        content = export_to_markdown(stats_list, inc_list)

    if output_path:
        save_export(content, output_path)
        console.print(f"[green]Report exported to {output_path}[/green]")
    else:
        click.echo(content)


@main.command("prune")
@click.option("--days", "-d", default=DEFAULT_RETENTION_DAYS, type=int, help="Retention threshold in days")
def prune(days: int) -> None:
    deleted = prune_logs(retention_days=days)
    console.print(f"[green]Pruned {deleted} check log entries older than {days} days.[/green]")


@main.command("gui")
def gui() -> None:
    from website_monitor.gui import run_gui
    run_gui()


if __name__ == "__main__":
    main()
