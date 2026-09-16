from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import List, Optional, Tuple
import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from api_cli.benchmarker import run_benchmark, render_benchmark_results
from api_cli.client import execute_request
from api_cli.config import DEFAULT_TIMEOUT_SECONDS, SUPPORTED_FORMATS
from api_cli.db import (
    clear_history,
    delete_environment,
    delete_saved_request,
    get_active_environment,
    get_environment,
    get_history_entry,
    get_saved_request,
    list_environments,
    list_history,
    list_saved_requests,
    save_environment,
    save_request,
    set_active_environment,
)
from api_cli.exporter import export_data
from api_cli.filter import FilterError, filter_payload
from api_cli.formatter import (
    get_status_color,
    render_headers,
    render_json,
    render_response_summary,
    render_table,
    render_verbose_request,
)
from api_cli.models import Environment, RequestConfig, ResponseResult, SavedRequest

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console()


def parse_key_value_pairs(items: Tuple[str, ...]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in items:
        if ":" in item:
            k, v = item.split(":", 1)
            result[k.strip()] = v.strip()
        elif "=" in item:
            k, v = item.split("=", 1)
            result[k.strip()] = v.strip()
    return result


def process_response(
    result: ResponseResult,
    config: RequestConfig,
    format_type: str,
    filter_expr: Optional[str],
    fields_list: Optional[List[str]],
    export_path: Optional[str],
    verbose: bool,
) -> None:
    if verbose:
        render_verbose_request(console, config)

    render_response_summary(console, result)

    parsed_data = result.parsed_json()
    display_data = parsed_data if parsed_data is not None else result.body

    if parsed_data is not None and (filter_expr or fields_list):
        try:
            display_data = filter_payload(parsed_data, expression=filter_expr, fields=fields_list)
        except FilterError as err:
            console.print(f"[bold red]Filter Error:[/] {str(err)}")
            return

    if export_path:
        saved_file = export_data(display_data, export_path)
        console.print(f"[bold green]Exported output to:[/] [cyan]{saved_file}[/]")

    if format_type == "headers":
        render_headers(console, result.headers, title=f"Response Headers ({result.status_code})")
    elif format_type == "raw":
        sys.stdout.write(result.body + "\n")
    elif format_type == "table":
        render_table(console, display_data)
    else:
        render_json(console, display_data)


def dispatch_request(
    method: str,
    url: str,
    header: Tuple[str, ...],
    query: Tuple[str, ...],
    data: Optional[str],
    file: Optional[click.Path],
    env: Optional[str],
    filter_expr: Optional[str],
    fields: Optional[str],
    format_type: str,
    export: Optional[str],
    timeout: float,
    verbose: bool,
    verify: bool,
    no_history: bool,
) -> None:
    body_content = data
    if file is not None:
        path = Path(str(file))
        if path.exists() and path.is_file():
            body_content = path.read_text(encoding="utf-8")
        else:
            console.print(f"[bold red]File not found:[/] {file}")
            return

    headers_map = parse_key_value_pairs(header)
    query_map = parse_key_value_pairs(query)

    fields_list = [f.strip() for f in fields.split(",") if f.strip()] if fields else None

    config = RequestConfig(
        method=method.upper(),
        url=url,
        headers=headers_map,
        query_params=query_map,
        body=body_content,
        timeout=timeout,
        verify_ssl=verify,
        follow_redirects=True,
    )

    result = execute_request(
        config=config,
        env_name=env,
        save_to_history=not no_history,
    )

    process_response(
        result=result,
        config=config,
        format_type=format_type,
        filter_expr=filter_expr,
        fields_list=fields_list,
        export_path=export,
        verbose=verbose,
    )


@click.group()
@click.version_option(version="0.1.0", prog_name="api-cli")
def main() -> None:
    pass


@main.command("req")
@click.argument("url")
@click.option("-X", "--method", default="GET", help="HTTP Method (GET, POST, PUT, DELETE, PATCH, etc.)")
@click.option("-H", "--header", multiple=True, help="Header in 'Key: Value' format")
@click.option("-q", "--query", multiple=True, help="Query param in 'key=value' format")
@click.option("-d", "--data", default=None, help="Raw body content or JSON string")
@click.option("-f", "--file", type=click.Path(exists=True, dir_okay=False), default=None, help="File with body data")
@click.option("-e", "--env", default=None, help="Environment profile to use")
@click.option("--filter", "filter_expr", default=None, help="JMESPath filter expression")
@click.option("--fields", default=None, help="Comma-separated field names to pick")
@click.option(
    "--format",
    "format_type",
    type=click.Choice(list(SUPPORTED_FORMATS)),
    default="json",
    help="Output format: json, table, raw, headers",
)
@click.option("--export", default=None, help="File path to export output (json, csv, md, txt)")
@click.option("--timeout", default=DEFAULT_TIMEOUT_SECONDS, type=float, help="Request timeout in seconds")
@click.option("-v", "--verbose", is_flag=True, help="Show full verbose request and headers")
@click.option("--verify/--no-verify", default=True, help="Verify SSL certificates")
@click.option("--no-history", is_flag=True, help="Do not store this request in history")
def request_command(
    url: str,
    method: str,
    header: Tuple[str, ...],
    query: Tuple[str, ...],
    data: Optional[str],
    file: Optional[click.Path],
    env: Optional[str],
    filter_expr: Optional[str],
    fields: Optional[str],
    format_type: str,
    export: Optional[str],
    timeout: float,
    verbose: bool,
    verify: bool,
    no_history: bool,
) -> None:
    dispatch_request(
        method=method,
        url=url,
        header=header,
        query=query,
        data=data,
        file=file,
        env=env,
        filter_expr=filter_expr,
        fields=fields,
        format_type=format_type,
        export=export,
        timeout=timeout,
        verbose=verbose,
        verify=verify,
        no_history=no_history,
    )


@main.command("get")
@click.argument("url")
@click.option("-H", "--header", multiple=True, help="Header in 'Key: Value' format")
@click.option("-q", "--query", multiple=True, help="Query param in 'key=value' format")
@click.option("-e", "--env", default=None, help="Environment profile to use")
@click.option("--filter", "filter_expr", default=None, help="JMESPath filter expression")
@click.option("--fields", default=None, help="Comma-separated field names to pick")
@click.option(
    "--format",
    "format_type",
    type=click.Choice(list(SUPPORTED_FORMATS)),
    default="json",
    help="Output format: json, table, raw, headers",
)
@click.option("--export", default=None, help="File path to export output")
@click.option("--timeout", default=DEFAULT_TIMEOUT_SECONDS, type=float, help="Request timeout in seconds")
@click.option("-v", "--verbose", is_flag=True, help="Show full verbose request and headers")
@click.option("--verify/--no-verify", default=True, help="Verify SSL certificates")
@click.option("--no-history", is_flag=True, help="Do not store this request in history")
def get_command(
    url: str,
    header: Tuple[str, ...],
    query: Tuple[str, ...],
    env: Optional[str],
    filter_expr: Optional[str],
    fields: Optional[str],
    format_type: str,
    export: Optional[str],
    timeout: float,
    verbose: bool,
    verify: bool,
    no_history: bool,
) -> None:
    dispatch_request(
        method="GET",
        url=url,
        header=header,
        query=query,
        data=None,
        file=None,
        env=env,
        filter_expr=filter_expr,
        fields=fields,
        format_type=format_type,
        export=export,
        timeout=timeout,
        verbose=verbose,
        verify=verify,
        no_history=no_history,
    )


@main.command("post")
@click.argument("url")
@click.option("-H", "--header", multiple=True, help="Header in 'Key: Value' format")
@click.option("-q", "--query", multiple=True, help="Query param in 'key=value' format")
@click.option("-d", "--data", default=None, help="Request body raw string or JSON")
@click.option("-f", "--file", type=click.Path(exists=True, dir_okay=False), default=None, help="File with body data")
@click.option("-e", "--env", default=None, help="Environment profile to use")
@click.option("--filter", "filter_expr", default=None, help="JMESPath filter expression")
@click.option("--fields", default=None, help="Comma-separated field names to pick")
@click.option(
    "--format",
    "format_type",
    type=click.Choice(list(SUPPORTED_FORMATS)),
    default="json",
    help="Output format: json, table, raw, headers",
)
@click.option("--export", default=None, help="File path to export output")
@click.option("--timeout", default=DEFAULT_TIMEOUT_SECONDS, type=float, help="Request timeout in seconds")
@click.option("-v", "--verbose", is_flag=True, help="Show full verbose request and headers")
@click.option("--verify/--no-verify", default=True, help="Verify SSL certificates")
@click.option("--no-history", is_flag=True, help="Do not store this request in history")
def post_command(
    url: str,
    header: Tuple[str, ...],
    query: Tuple[str, ...],
    data: Optional[str],
    file: Optional[click.Path],
    env: Optional[str],
    filter_expr: Optional[str],
    fields: Optional[str],
    format_type: str,
    export: Optional[str],
    timeout: float,
    verbose: bool,
    verify: bool,
    no_history: bool,
) -> None:
    dispatch_request(
        method="POST",
        url=url,
        header=header,
        query=query,
        data=data,
        file=file,
        env=env,
        filter_expr=filter_expr,
        fields=fields,
        format_type=format_type,
        export=export,
        timeout=timeout,
        verbose=verbose,
        verify=verify,
        no_history=no_history,
    )


@main.command("put")
@click.argument("url")
@click.option("-H", "--header", multiple=True, help="Header in 'Key: Value' format")
@click.option("-q", "--query", multiple=True, help="Query param in 'key=value' format")
@click.option("-d", "--data", default=None, help="Request body raw string or JSON")
@click.option("-f", "--file", type=click.Path(exists=True, dir_okay=False), default=None, help="File with body data")
@click.option("-e", "--env", default=None, help="Environment profile to use")
@click.option(
    "--format",
    "format_type",
    type=click.Choice(list(SUPPORTED_FORMATS)),
    default="json",
    help="Output format: json, table, raw, headers",
)
@click.option("--export", default=None, help="File path to export output")
@click.option("-v", "--verbose", is_flag=True, help="Show full verbose request and headers")
def put_command(
    url: str,
    header: Tuple[str, ...],
    query: Tuple[str, ...],
    data: Optional[str],
    file: Optional[click.Path],
    env: Optional[str],
    format_type: str,
    export: Optional[str],
    verbose: bool,
) -> None:
    dispatch_request(
        method="PUT",
        url=url,
        header=header,
        query=query,
        data=data,
        file=file,
        env=env,
        filter_expr=None,
        fields=None,
        format_type=format_type,
        export=export,
        timeout=DEFAULT_TIMEOUT_SECONDS,
        verbose=verbose,
        verify=True,
        no_history=False,
    )


@main.command("patch")
@click.argument("url")
@click.option("-H", "--header", multiple=True, help="Header in 'Key: Value' format")
@click.option("-q", "--query", multiple=True, help="Query param in 'key=value' format")
@click.option("-d", "--data", default=None, help="Request body raw string or JSON")
@click.option("-e", "--env", default=None, help="Environment profile to use")
@click.option(
    "--format",
    "format_type",
    type=click.Choice(list(SUPPORTED_FORMATS)),
    default="json",
    help="Output format: json, table, raw, headers",
)
@click.option("--export", default=None, help="File path to export output")
@click.option("-v", "--verbose", is_flag=True, help="Show full verbose request and headers")
def patch_command(
    url: str,
    header: Tuple[str, ...],
    query: Tuple[str, ...],
    data: Optional[str],
    env: Optional[str],
    format_type: str,
    export: Optional[str],
    verbose: bool,
) -> None:
    dispatch_request(
        method="PATCH",
        url=url,
        header=header,
        query=query,
        data=data,
        file=None,
        env=env,
        filter_expr=None,
        fields=None,
        format_type=format_type,
        export=export,
        timeout=DEFAULT_TIMEOUT_SECONDS,
        verbose=verbose,
        verify=True,
        no_history=False,
    )


@main.command("delete")
@click.argument("url")
@click.option("-H", "--header", multiple=True, help="Header in 'Key: Value' format")
@click.option("-e", "--env", default=None, help="Environment profile to use")
@click.option(
    "--format",
    "format_type",
    type=click.Choice(list(SUPPORTED_FORMATS)),
    default="json",
    help="Output format: json, table, raw, headers",
)
@click.option("-v", "--verbose", is_flag=True, help="Show full verbose request and headers")
def delete_command(
    url: str,
    header: Tuple[str, ...],
    env: Optional[str],
    format_type: str,
    verbose: bool,
) -> None:
    dispatch_request(
        method="DELETE",
        url=url,
        header=header,
        query=(),
        data=None,
        file=None,
        env=env,
        filter_expr=None,
        fields=None,
        format_type=format_type,
        export=None,
        timeout=DEFAULT_TIMEOUT_SECONDS,
        verbose=verbose,
        verify=True,
        no_history=False,
    )


@main.group("env")
def env_group() -> None:
    pass


@env_group.command("list")
def env_list_cmd() -> None:
    envs = list_environments()
    active = get_active_environment()

    if not envs:
        console.print("[yellow]No environments configured. Use 'api env set <name>' to create one.[/]")
        return

    table = Table(title="Environments", box=box.ROUNDED, header_style="bold cyan")
    table.add_column("Active", justify="center", style="bold green")
    table.add_column("Name", style="bold white")
    table.add_column("Base URL", style="cyan")
    table.add_column("Variables", style="yellow")
    table.add_column("Headers", style="dim")

    for e in envs:
        is_active = "[green]✓[/]" if e.name == active else ""
        var_count = str(len(e.variables))
        hdr_count = str(len(e.headers))
        table.add_row(is_active, e.name, e.base_url or "[dim]None[/]", f"{var_count} vars", f"{hdr_count} headers")

    console.print(table)


@env_group.command("set")
@click.argument("name")
@click.option("--base-url", default=None, help="Base URL for the environment")
@click.option("-v", "--var", multiple=True, help="Variable in key=value format")
@click.option("-H", "--header", multiple=True, help="Default header in Key: Value format")
def env_set_cmd(name: str, base_url: Optional[str], var: Tuple[str, ...], header: Tuple[str, ...]) -> None:
    existing = get_environment(name)
    now = datetime.now(timezone.utc).isoformat()

    final_base_url = base_url if base_url is not None else (existing.base_url if existing else "")
    final_vars = existing.variables.copy() if existing else {}
    final_vars.update(parse_key_value_pairs(var))

    final_headers = existing.headers.copy() if existing else {}
    final_headers.update(parse_key_value_pairs(header))

    env = Environment(
        name=name,
        base_url=final_base_url,
        headers=final_headers,
        variables=final_vars,
        updated_at=now,
    )
    save_environment(env)
    console.print(f"[bold green]Saved environment:[/] [cyan]{name}[/]")


@env_group.command("use")
@click.argument("name", required=False)
@click.option("--clear", is_flag=True, help="Clear active environment")
def env_use_cmd(name: Optional[str], clear: bool) -> None:
    if clear or not name:
        set_active_environment(None)
        console.print("[yellow]Cleared active environment.[/]")
        return

    env = get_environment(name)
    if not env:
        console.print(f"[bold red]Environment not found:[/] {name}")
        return

    set_active_environment(name)
    console.print(f"[bold green]Active environment switched to:[/] [cyan]{name}[/]")


@env_group.command("current")
def env_current_cmd() -> None:
    active = get_active_environment()
    if not active:
        console.print("[yellow]No active environment currently set.[/]")
        return

    env = get_environment(active)
    if not env:
        console.print(f"[yellow]Active environment '[/][cyan]{active}[/][yellow]' no longer exists.[/]")
        return

    console.print(f"[bold green]Active Environment:[/] [bold cyan]{env.name}[/]")
    if env.base_url:
        console.print(f"[dim]Base URL:[/] {env.base_url}")
    if env.variables:
        console.print("[dim]Variables:[/]")
        for k, v in env.variables.items():
            console.print(f"  {k} = {v}")
    if env.headers:
        console.print("[dim]Headers:[/]")
        for k, v in env.headers.items():
            console.print(f"  {k}: {v}")


@env_group.command("show")
@click.argument("name")
def env_show_cmd(name: str) -> None:
    env = get_environment(name)
    if not env:
        console.print(f"[bold red]Environment not found:[/] {name}")
        return

    table = Table(title=f"Environment: {name}", box=box.ROUNDED)
    table.add_column("Property", style="bold white")
    table.add_column("Value", style="cyan")
    table.add_row("Base URL", env.base_url or "[dim]None[/]")
    table.add_row("Updated At", env.updated_at)
    console.print(table)

    if env.variables:
        var_table = Table(title="Variables", box=box.ROUNDED)
        var_table.add_column("Key", style="bold white")
        var_table.add_column("Value", style="yellow")
        for k, v in env.variables.items():
            var_table.add_row(k, v)
        console.print(var_table)

    if env.headers:
        hdr_table = Table(title="Headers", box=box.ROUNDED)
        hdr_table.add_column("Header", style="bold white")
        hdr_table.add_column("Value", style="green")
        for k, v in env.headers.items():
            hdr_table.add_row(k, v)
        console.print(hdr_table)


@env_group.command("delete")
@click.argument("name")
def env_delete_cmd(name: str) -> None:
    deleted = delete_environment(name)
    if deleted:
        console.print(f"[bold green]Deleted environment:[/] {name}")
    else:
        console.print(f"[bold red]Environment not found:[/] {name}")


@main.group("saved")
def saved_group() -> None:
    pass


@saved_group.command("save")
@click.argument("name")
@click.argument("url")
@click.option("-X", "--method", default="GET", help="HTTP Method")
@click.option("-H", "--header", multiple=True, help="Header in 'Key: Value' format")
@click.option("-q", "--query", multiple=True, help="Query param in 'key=value' format")
@click.option("-d", "--data", default=None, help="Body payload")
@click.option("-e", "--env", default=None, help="Default environment profile")
def saved_save_cmd(
    name: str,
    url: str,
    method: str,
    header: Tuple[str, ...],
    query: Tuple[str, ...],
    data: Optional[str],
    env: Optional[str],
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    req = SavedRequest(
        name=name,
        method=method.upper(),
        url=url,
        headers=parse_key_value_pairs(header),
        query_params=parse_key_value_pairs(query),
        body=data,
        env_name=env,
        created_at=now,
    )
    save_request(req)
    console.print(f"[bold green]Saved request:[/] [cyan]{name}[/] ({req.method} {req.url})")


@saved_group.command("list")
def saved_list_cmd() -> None:
    requests = list_saved_requests()
    if not requests:
        console.print("[yellow]No saved requests found. Use 'api saved save <name> <url>' to add one.[/]")
        return

    table = Table(title="Saved Requests", box=box.ROUNDED, header_style="bold cyan")
    table.add_column("Name", style="bold white")
    table.add_column("Method", style="bold yellow")
    table.add_column("URL", style="cyan")
    table.add_column("Env", style="magenta")
    table.add_column("Created", style="dim")

    for r in requests:
        table.add_row(r.name, r.method, r.url, r.env_name or "-", r.created_at[:19])
    console.print(table)


@saved_group.command("run")
@click.argument("name")
@click.option("-e", "--env", default=None, help="Override environment profile")
@click.option("--filter", "filter_expr", default=None, help="JMESPath filter expression")
@click.option("--fields", default=None, help="Comma-separated field names to pick")
@click.option(
    "--format",
    "format_type",
    type=click.Choice(list(SUPPORTED_FORMATS)),
    default="json",
    help="Output format: json, table, raw, headers",
)
@click.option("--export", default=None, help="File path to export output")
@click.option("-v", "--verbose", is_flag=True, help="Show full verbose request and headers")
def saved_run_cmd(
    name: str,
    env: Optional[str],
    filter_expr: Optional[str],
    fields: Optional[str],
    format_type: str,
    export: Optional[str],
    verbose: bool,
) -> None:
    saved = get_saved_request(name)
    if not saved:
        console.print(f"[bold red]Saved request not found:[/] {name}")
        return

    fields_list = [f.strip() for f in fields.split(",") if f.strip()] if fields else None
    target_env = env or saved.env_name

    config = RequestConfig(
        method=saved.method,
        url=saved.url,
        headers=saved.headers,
        query_params=saved.query_params,
        body=saved.body,
        timeout=DEFAULT_TIMEOUT_SECONDS,
        verify_ssl=True,
        follow_redirects=True,
    )

    result = execute_request(config=config, env_name=target_env, save_to_history=True)

    process_response(
        result=result,
        config=config,
        format_type=format_type,
        filter_expr=filter_expr,
        fields_list=fields_list,
        export_path=export,
        verbose=verbose,
    )


@saved_group.command("delete")
@click.argument("name")
def saved_delete_cmd(name: str) -> None:
    deleted = delete_saved_request(name)
    if deleted:
        console.print(f"[bold green]Deleted saved request:[/] {name}")
    else:
        console.print(f"[bold red]Saved request not found:[/] {name}")


@main.group("history")
def history_group() -> None:
    pass


@history_group.command("list")
@click.option("--limit", default=20, type=int, help="Number of records to show")
def history_list_cmd(limit: int) -> None:
    items = list_history(limit=limit)
    if not items:
        console.print("[yellow]No request history found.[/]")
        return

    table = Table(title="Request History", box=box.ROUNDED, header_style="bold cyan")
    table.add_column("ID", style="dim", justify="right")
    table.add_column("Method", style="bold yellow")
    table.add_column("Status", justify="center")
    table.add_column("Latency", justify="right", style="cyan")
    table.add_column("URL", style="white")
    table.add_column("Timestamp", style="dim")

    for item in items:
        color = get_status_color(item.status_code)
        status_badge = f"[{color}]{item.status_code}[/]"
        lat_text = f"{item.latency_ms:.1f}ms"
        time_text = item.timestamp[:19] if item.timestamp else ""
        table.add_row(str(item.id), item.method, status_badge, lat_text, item.url, time_text)

    console.print(table)


@history_group.command("show")
@click.argument("entry_id", type=int)
def history_show_cmd(entry_id: int) -> None:
    entry = get_history_entry(entry_id)
    if not entry:
        console.print(f"[bold red]History entry not found:[/] ID {entry_id}")
        return

    color = get_status_color(entry.status_code)
    console.print(
        f"[{color}]{entry.status_code}[/] [bold yellow]{entry.method}[/] [cyan]{entry.url}[/] | "
        f"Latency: [bold cyan]{entry.latency_ms:.1f}ms[/] | Time: [dim]{entry.timestamp}[/]"
    )

    if entry.request_headers:
        render_headers(console, entry.request_headers, title="Request Headers")

    if entry.request_body:
        console.print(Panel(entry.request_body, title="Request Body", border_style="blue", box=box.ROUNDED))

    if entry.response_headers:
        render_headers(console, entry.response_headers, title="Response Headers")

    if entry.response_body:
        console.print("[bold]Response Body:[/]")
        render_json(console, entry.response_body)


@history_group.command("replay")
@click.argument("entry_id", type=int)
@click.option(
    "--format",
    "format_type",
    type=click.Choice(list(SUPPORTED_FORMATS)),
    default="json",
    help="Output format",
)
@click.option("--export", default=None, help="Export path")
def history_replay_cmd(entry_id: int, format_type: str, export: Optional[str]) -> None:
    entry = get_history_entry(entry_id)
    if not entry:
        console.print(f"[bold red]History entry not found:[/] ID {entry_id}")
        return

    console.print(f"[cyan]Replaying request ID {entry_id}:[/] {entry.method} {entry.url}")

    config = RequestConfig(
        method=entry.method,
        url=entry.url,
        headers=entry.request_headers,
        body=entry.request_body,
        timeout=DEFAULT_TIMEOUT_SECONDS,
        verify_ssl=True,
        follow_redirects=True,
    )

    result = execute_request(config=config, save_to_history=True)

    process_response(
        result=result,
        config=config,
        format_type=format_type,
        filter_expr=None,
        fields_list=None,
        export_path=export,
        verbose=False,
    )


@history_group.command("clear")
def history_clear_cmd() -> None:
    count = clear_history()
    console.print(f"[bold green]Cleared {count} history records.[/]")


@main.command("bench")
@click.argument("url")
@click.option("-X", "--method", default="GET", help="HTTP Method")
@click.option("-n", "--requests", default=10, type=int, help="Total number of requests to send")
@click.option("-c", "--concurrency", default=2, type=int, help="Number of concurrent workers")
@click.option("-H", "--header", multiple=True, help="Header in 'Key: Value' format")
@click.option("-d", "--data", default=None, help="Payload data")
@click.option("-e", "--env", default=None, help="Environment profile to use")
def bench_command(
    url: str,
    method: str,
    requests: int,
    concurrency: int,
    header: Tuple[str, ...],
    data: Optional[str],
    env: Optional[str],
) -> None:
    headers_map = parse_key_value_pairs(header)
    config = RequestConfig(
        method=method.upper(),
        url=url,
        headers=headers_map,
        body=data,
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )

    console.print(
        f"[bold cyan]Benchmarking:[/] {config.method} {url} ([bold]{requests}[/] requests, concurrency [bold]{concurrency}[/])..."
    )

    stats = run_benchmark(
        config=config,
        total_requests=requests,
        concurrency=concurrency,
        env_name=env,
    )

    render_benchmark_results(console, stats)


if __name__ == "__main__":
    main()
