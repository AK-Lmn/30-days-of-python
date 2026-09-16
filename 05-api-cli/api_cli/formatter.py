import json
from typing import Any, Dict, List
from rich import box
from rich.console import Console
from rich.json import JSON
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from api_cli.models import RequestConfig, ResponseResult


def get_status_color(status_code: int) -> str:
    if 200 <= status_code < 300:
        return "bold green"
    if 300 <= status_code < 400:
        return "bold yellow"
    if 400 <= status_code < 500:
        return "bold red"
    return "bold magenta"


def format_bytes(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    return f"{size_bytes / (1024 * 1024):.2f} MB"


def render_response_summary(console: Console, result: ResponseResult) -> None:
    status_color = get_status_color(result.status_code)
    status_text = f"[{status_color}]{result.status_code} {result.reason_phrase or 'OK'}[/]"
    latency_text = f"[bold cyan]{result.latency_ms:.1f}ms[/]"
    size_text = f"[bold blue]{format_bytes(result.size_bytes)}[/]"
    content_type = f"[dim]{result.content_type or 'unknown'}[/]"
    console.print(f"{status_text} | Time: {latency_text} | Size: {size_text} | Type: {content_type}")


def render_json(console: Console, data: Any) -> None:
    if isinstance(data, (dict, list)):
        payload_str = json.dumps(data)
        console.print(JSON(payload_str))
    elif isinstance(data, str):
        try:
            parsed = json.loads(data)
            console.print(JSON.from_data(parsed))
        except (ValueError, TypeError):
            console.print(data)
    else:
        console.print(str(data))


def render_headers(console: Console, headers: Dict[str, str], title: str = "Headers") -> None:
    table = Table(title=title, box=box.ROUNDED, header_style="bold cyan")
    table.add_column("Header", style="bold white")
    table.add_column("Value", style="green")
    for key, value in headers.items():
        table.add_row(key, str(value))
    console.print(table)


def render_table(console: Console, data: Any) -> None:
    if isinstance(data, list) and data and all(isinstance(item, dict) for item in data):
        columns: List[str] = []
        for item in data:
            for key in item.keys():
                if key not in columns:
                    columns.append(key)
        table = Table(box=box.ROUNDED, header_style="bold cyan")
        for col in columns:
            table.add_column(str(col), style="white")
        for item in data:
            row_cells = []
            for col in columns:
                val = item.get(col)
                if val is None:
                    row_cells.append("[dim]null[/]")
                elif isinstance(val, (dict, list)):
                    row_cells.append(json.dumps(val))
                else:
                    row_cells.append(str(val))
            table.add_row(*row_cells)
        console.print(table)
    elif isinstance(data, dict):
        table = Table(box=box.ROUNDED, header_style="bold cyan")
        table.add_column("Field", style="bold white")
        table.add_column("Value", style="green")
        for k, v in data.items():
            if isinstance(v, (dict, list)):
                formatted_val = json.dumps(v, indent=2)
            else:
                formatted_val = str(v)
            table.add_row(str(k), formatted_val)
        console.print(table)
    elif isinstance(data, list):
        table = Table(box=box.ROUNDED, header_style="bold cyan")
        table.add_column("Index", style="dim", justify="right")
        table.add_column("Value", style="white")
        for idx, item in enumerate(data):
            table.add_row(str(idx), str(item))
        console.print(table)
    else:
        console.print(str(data))


def render_verbose_request(console: Console, config: RequestConfig) -> None:
    lines = [f"[bold yellow]{config.method.upper()}[/] [cyan]{config.url}[/]"]
    if config.query_params:
        lines.append("\n[bold]Query Parameters:[/]")
        for k, v in config.query_params.items():
            lines.append(f"  [dim]{k}[/]: {v}")
    if config.headers:
        lines.append("\n[bold]Request Headers:[/]")
        for k, v in config.headers.items():
            lines.append(f"  [dim]{k}[/]: {v}")
    if config.body:
        lines.append(f"\n[bold]Request Body ({len(config.body.encode('utf-8'))} bytes):[/]\n{config.body}")
    console.print(Panel("\n".join(lines), title="Request Details", border_style="blue", box=box.ROUNDED))
