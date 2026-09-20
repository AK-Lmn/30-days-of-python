from pathlib import Path
import sys

import click
from rich.console import Console

from terminal_dashboard.alerts import evaluate_alerts, get_health_status
from terminal_dashboard.app import DashboardApp
from terminal_dashboard.collector import MetricsCollector
from terminal_dashboard.config import load_config, save_config
from terminal_dashboard.exporter import export_snapshot
from terminal_dashboard.models import DashboardConfig
from terminal_dashboard.views import (
    render_alerts_banner,
    render_cpu_panel,
    render_disk_panel,
    render_header,
    render_memory_panel,
    render_network_panel,
    render_process_panel,
)


if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


@click.group(invoke_without_command=True)
@click.option("--config", "-c", "config_path", type=click.Path(), default=None)
@click.pass_context
def main(ctx: click.Context, config_path: str | None) -> None:
    ctx.ensure_object(dict)
    cfg = load_config(config_path)
    ctx.obj["config"] = cfg

    if ctx.invoked_subcommand is None:
        ctx.invoke(live_cmd)


@main.command("live")
@click.option("--interval", "-i", type=float, default=None)
@click.option("--sort", "-s", type=click.Choice(["cpu", "mem", "name", "pid"]), default=None)
@click.option("--limit", "-l", type=int, default=None)
@click.pass_context
def live_cmd(ctx: click.Context, interval: float | None, sort: str | None, limit: int | None) -> None:
    cfg: DashboardConfig = ctx.obj["config"]
    if interval is not None:
        cfg.refresh_interval = interval
    if sort is not None:
        cfg.process_sort_by = sort
    if limit is not None:
        cfg.process_limit = limit

    app = DashboardApp(config=cfg)
    app.run()


@main.command("snapshot")
@click.pass_context
def snapshot_cmd(ctx: click.Context) -> None:
    cfg: DashboardConfig = ctx.obj["config"]
    collector = MetricsCollector()
    snapshot = collector.collect_snapshot(process_limit=cfg.process_limit, sort_by=cfg.process_sort_by)
    snapshot.alerts = evaluate_alerts(snapshot, cfg)

    console = Console()
    console.print(render_header(snapshot.system, snapshot.battery))
    console.print(render_alerts_banner(snapshot.alerts))
    console.print(render_cpu_panel(snapshot.cpu))
    console.print(render_memory_panel(snapshot.memory))
    console.print(render_disk_panel(snapshot.disk))
    console.print(render_network_panel(snapshot.network))
    console.print(render_process_panel(snapshot.processes, cfg.process_sort_by))


@main.command("cpu")
@click.pass_context
def cpu_cmd(ctx: click.Context) -> None:
    collector = MetricsCollector()
    cpu = collector.collect_cpu()
    console = Console()
    console.print(render_cpu_panel(cpu))


@main.command("mem")
@click.pass_context
def mem_cmd(ctx: click.Context) -> None:
    collector = MetricsCollector()
    memory = collector.collect_memory()
    console = Console()
    console.print(render_memory_panel(memory))


@main.command("disk")
@click.pass_context
def disk_cmd(ctx: click.Context) -> None:
    collector = MetricsCollector()
    disk = collector.collect_disk()
    console = Console()
    console.print(render_disk_panel(disk))


@main.command("net")
@click.pass_context
def net_cmd(ctx: click.Context) -> None:
    collector = MetricsCollector()
    network = collector.collect_network()
    console = Console()
    console.print(render_network_panel(network))


@main.command("proc")
@click.option("--sort", "-s", type=click.Choice(["cpu", "mem", "name", "pid"]), default="cpu")
@click.option("--limit", "-n", type=int, default=20)
@click.option("--search", "-q", type=str, default=None)
@click.pass_context
def proc_cmd(ctx: click.Context, sort: str, limit: int, search: str | None) -> None:
    collector = MetricsCollector()
    procs = collector.collect_processes(limit=limit if not search else 200, sort_by=sort)
    if search:
        search_lower = search.lower()
        procs = [p for p in procs if search_lower in p.name.lower() or search_lower in p.username.lower()][:limit]
    console = Console()
    console.print(render_process_panel(procs, sort_by=sort))


@main.command("check")
@click.pass_context
def check_cmd(ctx: click.Context) -> None:
    cfg: DashboardConfig = ctx.obj["config"]
    collector = MetricsCollector()
    snapshot = collector.collect_snapshot(process_limit=5, sort_by="cpu")
    alerts = evaluate_alerts(snapshot, cfg)
    code, status = get_health_status(alerts)

    console = Console()
    if code == 0:
        console.print("[bold green]HEALTHY[/bold green]: All system metrics normal.")
    elif code == 1:
        console.print("[bold yellow]WARNING[/bold yellow]: One or more system thresholds exceeded.")
        for a in alerts:
            console.print(f" - [{a.level.value}] {a.name}: {a.message}")
    else:
        console.print("[bold red]CRITICAL[/bold red]: One or more critical system thresholds exceeded!")
        for a in alerts:
            console.print(f" - [{a.level.value}] {a.name}: {a.message}")

    sys.exit(code)


@main.command("export")
@click.option("--format", "-f", "format_type", type=click.Choice(["json", "markdown", "md", "html"]), default="json")
@click.option("--output", "-o", "output_path", type=click.Path(), default=None)
@click.pass_context
def export_cmd(ctx: click.Context, format_type: str, output_path: str | None) -> None:
    cfg: DashboardConfig = ctx.obj["config"]
    collector = MetricsCollector()
    snapshot = collector.collect_snapshot(process_limit=cfg.process_limit, sort_by=cfg.process_sort_by)
    snapshot.alerts = evaluate_alerts(snapshot, cfg)

    result = export_snapshot(snapshot, format_type=format_type, output_path=output_path)
    console = Console()
    if output_path:
        console.print(f"[bold green]Successfully exported {format_type.upper()} to:[/bold green] {output_path}")
    else:
        console.print(result)


@main.command("config-show")
@click.pass_context
def config_show_cmd(ctx: click.Context) -> None:
    cfg: DashboardConfig = ctx.obj["config"]
    console = Console()
    for k, v in cfg.to_dict().items():
        console.print(f"[cyan]{k}[/cyan] = [white]{v}[/white]")


@main.command("config-init")
@click.option("--path", "-p", "target_path", type=click.Path(), default=None)
@click.pass_context
def config_init_cmd(ctx: click.Context, target_path: str | None) -> None:
    cfg = DashboardConfig()
    written_path = save_config(cfg, target_path)
    console = Console()
    console.print(f"[bold green]Wrote default configuration to:[/bold green] {written_path}")


if __name__ == "__main__":
    main()
