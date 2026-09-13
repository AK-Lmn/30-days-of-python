from typing import Optional
from rich.box import ROUNDED
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from github_analyzer.models import (
    ComparisonResult,
    RateLimitStatus,
    RepoAnalysis,
    UserAnalysis,
)


def create_language_bar(percentage: float, width: int = 24) -> str:
    filled_length = int(round(width * (percentage / 100)))
    empty_length = max(0, width - filled_length)
    return f"[{'=' * filled_length}{'.' * empty_length}]"


def render_user_analysis(analysis: UserAnalysis, console: Optional[Console] = None) -> None:
    c = console or Console()
    u = analysis.user

    bio_text = u.bio or "No bio provided."
    details = []
    if u.company:
        details.append(f"Company: {u.company}")
    if u.location:
        details.append(f"Location: {u.location}")
    if u.blog:
        details.append(f"Website: {u.blog}")
    details.append(f"Joined: {u.created_at.strftime('%b %d, %Y')}")

    header_text = Text()
    display_name = u.name or u.login
    header_text.append(f"{display_name} ", style="bold cyan")
    header_text.append(f"(@{u.login})\n", style="dim")
    header_text.append(f"{bio_text}\n\n", style="italic")
    header_text.append(" | ".join(details), style="bright_black")

    c.print(Panel(header_text, title="GitHub User Profile", border_style="cyan", box=ROUNDED))

    summary_table = Table(box=ROUNDED, show_header=True, header_style="bold magenta", expand=True)
    summary_table.add_column("Public Repos", justify="center")
    summary_table.add_column("Source Repos", justify="center")
    summary_table.add_column("Forked Repos", justify="center")
    summary_table.add_column("Followers", justify="center")
    summary_table.add_column("Total Stars", justify="center", style="yellow")
    summary_table.add_column("Total Forks", justify="center", style="blue")

    summary_table.add_row(
        str(u.public_repos),
        str(analysis.source_repositories_count),
        str(analysis.forked_repositories_count),
        f"{u.followers:,}",
        f"{analysis.total_stars:,}",
        f"{analysis.total_forks:,}",
    )
    c.print(summary_table)

    if analysis.languages.languages:
        lang_table = Table(title="Top Languages Across Repositories", box=ROUNDED, expand=True)
        lang_table.add_column("Language", style="cyan", width=20)
        lang_table.add_column("Distribution", style="green", width=28)
        lang_table.add_column("Percentage", justify="right", style="bold", width=12)

        for lang in analysis.languages.languages[:8]:
            bar = create_language_bar(lang.percentage, width=20)
            lang_table.add_row(lang.name, bar, f"{lang.percentage:.1f}%")
        c.print(lang_table)

    if analysis.top_starred_repos:
        repo_table = Table(title="Top Starred Repositories", box=ROUNDED, expand=True)
        repo_table.add_column("Repository", style="bold cyan")
        repo_table.add_column("Language", style="green")
        repo_table.add_column("Stars", justify="right", style="yellow")
        repo_table.add_column("Forks", justify="right", style="blue")
        repo_table.add_column("Description", style="dim")

        for r in analysis.top_starred_repos:
            desc = (r.description[:55] + "...") if r.description and len(r.description) > 55 else (r.description or "-")
            repo_table.add_row(
                r.name,
                r.language or "-",
                f"{r.stars:,}",
                f"{r.forks:,}",
                desc,
            )
        c.print(repo_table)


def render_repo_analysis(analysis: RepoAnalysis, console: Optional[Console] = None) -> None:
    c = console or Console()
    r = analysis.repository

    header_text = Text()
    header_text.append(f"{r.full_name}\n", style="bold green")
    desc = r.description or "No description provided."
    header_text.append(f"{desc}\n\n", style="italic")

    meta_items = [
        f"Branch: {r.default_branch}",
        f"License: {r.license_name or 'None'}",
        f"Size: {r.size_kb:,} KB",
        f"Created: {r.created_at.strftime('%Y-%m-%d')}",
    ]
    if r.pushed_at:
        meta_items.append(f"Last Push: {r.pushed_at.strftime('%Y-%m-%d')}")
    header_text.append(" | ".join(meta_items), style="dim")

    c.print(Panel(header_text, title="Repository Overview", border_style="green", box=ROUNDED))

    metrics_table = Table(box=ROUNDED, expand=True, header_style="bold yellow")
    metrics_table.add_column("Stars", justify="center")
    metrics_table.add_column("Forks", justify="center")
    metrics_table.add_column("Watchers", justify="center")
    metrics_table.add_column("Open Issues", justify="center")
    metrics_table.add_column("Health Score", justify="center")

    health_style = "bold green" if analysis.health.health_score >= 80 else ("yellow" if analysis.health.health_score >= 50 else "red")

    metrics_table.add_row(
        f"{r.stars:,}",
        f"{r.forks:,}",
        f"{r.watchers:,}",
        f"{r.open_issues:,}",
        Text(f"{analysis.health.health_score}/100", style=health_style),
    )
    c.print(metrics_table)

    if analysis.languages.languages:
        lang_table = Table(title="Language Composition (Codebase Bytes)", box=ROUNDED, expand=True)
        lang_table.add_column("Language", style="cyan", width=20)
        lang_table.add_column("Distribution", style="green", width=28)
        lang_table.add_column("Percentage", justify="right", style="bold", width=12)
        lang_table.add_column("Bytes", justify="right", style="dim", width=14)

        for lang in analysis.languages.languages:
            bar = create_language_bar(lang.percentage, width=20)
            lang_table.add_row(lang.name, bar, f"{lang.percentage:.1f}%", f"{lang.bytes_count:,}")
        c.print(lang_table)

    if analysis.commit_analytics.total_sampled_commits > 0:
        commit_table = Table(title="Commit Velocity & Activity Patterns (Sampled)", box=ROUNDED, expand=True)
        commit_table.add_column("Metric", style="cyan")
        commit_table.add_column("Details", style="white")

        top_committer_str = ", ".join(f"{name} ({count})" for name, count in analysis.commit_analytics.top_committers.items())
        weekdays_str = ", ".join(f"{day[:3]}: {count}" for day, count in analysis.commit_analytics.commits_by_weekday.items())

        commit_table.add_row("Total Commits Sampled", str(analysis.commit_analytics.total_sampled_commits))
        commit_table.add_row("Top Authors", top_committer_str or "None")
        commit_table.add_row("Activity by Weekday", weekdays_str or "None")
        c.print(commit_table)

    if analysis.contributors:
        contrib_table = Table(title="Top Contributors", box=ROUNDED, expand=True)
        contrib_table.add_column("Contributor", style="bold cyan")
        contrib_table.add_column("Contributions", justify="right", style="green")

        for contrib in analysis.contributors[:10]:
            contrib_table.add_row(contrib.login, f"{contrib.contributions:,}")
        c.print(contrib_table)


def render_comparison(comparison: ComparisonResult, console: Optional[Console] = None) -> None:
    c = console or Console()

    table = Table(title=comparison.title, box=ROUNDED, expand=True)
    table.add_column("Metric", style="bold white", width=24)
    table.add_column(comparison.item1_name, style="cyan", justify="center")
    table.add_column(comparison.item2_name, style="magenta", justify="center")

    for m in comparison.metrics:
        val1_text = Text(m.value1)
        val2_text = Text(m.value2)
        if m.winner == 1:
            val1_text.stylize("bold green")
            val1_text.append(" [WINNER]")
        elif m.winner == 2:
            val2_text.stylize("bold green")
            val2_text.append(" [WINNER]")

        table.add_row(m.name, val1_text, val2_text)

    c.print(table)


def render_rate_limit(status: RateLimitStatus, console: Optional[Console] = None) -> None:
    c = console or Console()

    used_percentage = round((status.used / status.limit) * 100, 1) if status.limit > 0 else 0
    bar = create_language_bar(used_percentage, width=24)

    text = Text()
    text.append("GitHub REST API Rate Limit Status\n\n", style="bold cyan")
    text.append(f"Limit:      {status.limit:,} requests/hr\n")
    text.append(f"Remaining:  {status.remaining:,} requests\n", style="bold green" if status.remaining > 10 else "bold red")
    text.append(f"Used:       {status.used:,} ({used_percentage}% used)\n")
    text.append(f"Quota Bar:  {bar}\n")
    text.append(f"Reset At:   {status.reset_time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n", style="dim")

    c.print(Panel(text, title="Rate Limit Quota", border_style="cyan", box=ROUNDED))
