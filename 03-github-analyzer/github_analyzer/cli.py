from pathlib import Path
from typing import Optional
import click
from rich.console import Console

from github_analyzer import __version__
from github_analyzer.analyzer import (
    analyze_repo,
    analyze_user,
    compare_repositories,
    compare_users,
)
from github_analyzer.cache import ResponseCache
from github_analyzer.client import (
    AuthenticationError,
    GitHubAPIError,
    GitHubClient,
    RateLimitExceededError,
    ResourceNotFoundError,
)
from github_analyzer.exporter import (
    export_repo_to_markdown,
    export_repo_to_json,
    export_user_to_markdown,
    export_user_to_json,
    save_export_file,
)
from github_analyzer.views import (
    render_comparison,
    render_rate_limit,
    render_repo_analysis,
    render_user_analysis,
)

console = Console()


@click.group()
@click.version_option(__version__, prog_name="github-analyzer")
@click.option("--token", envvar="GITHUB_TOKEN", help="GitHub Personal Access Token for higher rate limits.")
@click.option("--no-cache", is_flag=True, help="Bypass local response cache.")
@click.option("--timeout", default=15.0, type=float, help="Network request timeout in seconds.")
@click.pass_context
def main(ctx: click.Context, token: Optional[str], no_cache: bool, timeout: float) -> None:
    ctx.ensure_object(dict)
    cache = ResponseCache() if not no_cache else None
    client = GitHubClient(token=token, cache=cache, use_cache=not no_cache, timeout=timeout)
    ctx.obj["client"] = client
    ctx.obj["cache"] = cache


@main.command()
@click.argument("username")
@click.option("--include-forks", is_flag=True, help="Include forked repositories in metrics.")
@click.option("--max-repos", default=200, type=int, help="Maximum number of repositories to inspect.")
@click.option("--export", type=click.Choice(["json", "md"], case_sensitive=False), help="Export format.")
@click.option("--output", type=click.Path(dir_okay=False, writable=True, path_type=Path), help="File path to write export.")
@click.pass_context
def user(
    ctx: click.Context,
    username: str,
    include_forks: bool,
    max_repos: int,
    export: Optional[str],
    output: Optional[Path],
) -> None:
    client: GitHubClient = ctx.obj["client"]
    try:
        with console.status(f"[bold cyan]Analyzing GitHub user @{username}..."):
            analysis = analyze_user(
                client=client,
                username=username,
                include_forks=include_forks,
                max_repos=max_repos,
            )
    except ResourceNotFoundError:
        console.print(f"[bold red]Error:[/] User '[cyan]{username}[/]' was not found on GitHub.")
        raise click.Abort()
    except RateLimitExceededError as exc:
        console.print(f"[bold red]Rate Limit Exceeded:[/] {exc}")
        console.print("[dim]Tip: Provide a personal access token using --token or set the GITHUB_TOKEN environment variable.[/]")
        raise click.Abort()
    except AuthenticationError as exc:
        console.print(f"[bold red]Authentication Error:[/] {exc}")
        raise click.Abort()
    except GitHubAPIError as exc:
        console.print(f"[bold red]API Error:[/] {exc}")
        raise click.Abort()

    render_user_analysis(analysis, console=console)

    if export:
        content = export_user_to_json(analysis) if export.lower() == "json" else export_user_to_markdown(analysis)
        target_file = output or Path(f"{username}_github_analysis.{export.lower()}")
        save_export_file(content, target_file)
        console.print(f"\n[bold green]Report exported successfully to:[/] {target_file}")


@main.command()
@click.argument("target")
@click.option("--export", type=click.Choice(["json", "md"], case_sensitive=False), help="Export format.")
@click.option("--output", type=click.Path(dir_okay=False, writable=True, path_type=Path), help="File path to write export.")
@click.pass_context
def repo(
    ctx: click.Context,
    target: str,
    export: Optional[str],
    output: Optional[Path],
) -> None:
    client: GitHubClient = ctx.obj["client"]
    if "/" not in target:
        console.print("[bold red]Error:[/] Target repository must be in 'owner/repo' format (e.g. pallets/click).")
        raise click.Abort()

    owner, repo_name = target.split("/", 1)
    try:
        with console.status(f"[bold green]Analyzing repository {owner}/{repo_name}..."):
            analysis = analyze_repo(client=client, owner=owner, repo=repo_name)
    except ResourceNotFoundError:
        console.print(f"[bold red]Error:[/] Repository '[cyan]{target}[/]' was not found on GitHub.")
        raise click.Abort()
    except RateLimitExceededError as exc:
        console.print(f"[bold red]Rate Limit Exceeded:[/] {exc}")
        console.print("[dim]Tip: Provide a personal access token using --token or set the GITHUB_TOKEN environment variable.[/]")
        raise click.Abort()
    except AuthenticationError as exc:
        console.print(f"[bold red]Authentication Error:[/] {exc}")
        raise click.Abort()
    except GitHubAPIError as exc:
        console.print(f"[bold red]API Error:[/] {exc}")
        raise click.Abort()

    render_repo_analysis(analysis, console=console)

    if export:
        content = export_repo_to_json(analysis) if export.lower() == "json" else export_repo_to_markdown(analysis)
        safe_name = f"{owner}_{repo_name}".replace("/", "_")
        target_file = output or Path(f"{safe_name}_repo_analysis.{export.lower()}")
        save_export_file(content, target_file)
        console.print(f"\n[bold green]Report exported successfully to:[/] {target_file}")


@main.command()
@click.argument("target1")
@click.argument("target2")
@click.option(
    "--type",
    "compare_type",
    type=click.Choice(["auto", "repo", "user"], case_sensitive=False),
    default="auto",
    help="Explicitly specify whether comparing repositories or users.",
)
@click.pass_context
def compare(
    ctx: click.Context,
    target1: str,
    target2: str,
    compare_type: str,
) -> None:
    client: GitHubClient = ctx.obj["client"]

    is_repo_mode = False
    if compare_type == "repo":
        is_repo_mode = True
    elif compare_type == "user":
        is_repo_mode = False
    else:
        is_repo_mode = "/" in target1 or "/" in target2

    try:
        if is_repo_mode:
            if "/" not in target1 or "/" not in target2:
                console.print("[bold red]Error:[/] When comparing repositories, both targets must be 'owner/repo'.")
                raise click.Abort()
            o1, r1 = target1.split("/", 1)
            o2, r2 = target2.split("/", 1)
            with console.status("[bold magenta]Fetching and comparing repositories..."):
                analysis1 = analyze_repo(client, o1, r1)
                analysis2 = analyze_repo(client, o2, r2)
            result = compare_repositories(analysis1, analysis2)
        else:
            with console.status("[bold magenta]Fetching and comparing users..."):
                analysis1 = analyze_user(client, target1)
                analysis2 = analyze_user(client, target2)
            result = compare_users(analysis1, analysis2)
    except ResourceNotFoundError as exc:
        console.print(f"[bold red]Error:[/] {exc}")
        raise click.Abort()
    except RateLimitExceededError as exc:
        console.print(f"[bold red]Rate Limit Exceeded:[/] {exc}")
        raise click.Abort()
    except GitHubAPIError as exc:
        console.print(f"[bold red]API Error:[/] {exc}")
        raise click.Abort()

    render_comparison(result, console=console)


@main.command("rate-limit")
@click.pass_context
def rate_limit_cmd(ctx: click.Context) -> None:
    client: GitHubClient = ctx.obj["client"]
    try:
        status = client.get_rate_limit()
        render_rate_limit(status, console=console)
    except GitHubAPIError as exc:
        console.print(f"[bold red]Failed to retrieve rate limit:[/] {exc}")
        raise click.Abort()


@main.group()
def cache() -> None:
    pass


@cache.command("clear")
def cache_clear() -> None:
    c = ResponseCache()
    cleared = c.clear()
    console.print(f"[bold green]Cache cleared successfully.[/] Deleted [cyan]{cleared}[/] cached records.")


@cache.command("status")
def cache_status() -> None:
    c = ResponseCache()
    pruned = c.prune_expired()
    console.print(f"[bold green]Pruned [cyan]{pruned}[/] expired records from cache database: {c.db_path}")


@main.command()
def gui() -> None:
    from github_analyzer.gui import run_gui
    run_gui()
