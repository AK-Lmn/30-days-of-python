import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from github_analyzer.models import RepoAnalysis, UserAnalysis


class DateTimeEncoder(json.JSONEncoder):
    def default(self, o: Any) -> Any:
        if isinstance(o, datetime):
            return o.isoformat()
        if is_dataclass(o):
            return asdict(o)
        return super().default(o)


def export_user_to_json(analysis: UserAnalysis) -> str:
    data = asdict(analysis)
    return json.dumps(data, indent=2, cls=DateTimeEncoder)


def export_user_to_markdown(analysis: UserAnalysis) -> str:
    u = analysis.user
    lines = [
        f"# GitHub Analysis: {u.login}",
        "",
        f"**Name:** {u.name or u.login}  ",
        f"**Bio:** {u.bio or 'N/A'}  ",
        f"**Location:** {u.location or 'N/A'}  ",
        f"**Company:** {u.company or 'N/A'}  ",
        f"**Website:** {u.blog or 'N/A'}  ",
        f"**Account Created:** {u.created_at.strftime('%Y-%m-%d')}  ",
        f"**Profile URL:** {u.html_url}  ",
        "",
        "## Summary Metrics",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Public Repositories | {u.public_repos:,} |",
        f"| Source Repositories | {analysis.source_repositories_count:,} |",
        f"| Forked Repositories | {analysis.forked_repositories_count:,} |",
        f"| Total Followers | {u.followers:,} |",
        f"| Total Following | {u.following:,} |",
        f"| Total Stars Earned | {analysis.total_stars:,} |",
        f"| Total Forks Earned | {analysis.total_forks:,} |",
        "",
        "## Languages",
        "",
        "| Language | Percentage |",
        "|---|---|",
    ]

    for lang in analysis.languages.languages:
        lines.append(f"| {lang.name} | {lang.percentage:.1f}% |")

    lines.extend([
        "",
        "## Top Starred Repositories",
        "",
        "| Repository | Language | Stars | Forks |",
        "|---|---|---|---|",
    ])

    for r in analysis.top_starred_repos:
        lines.append(f"| [{r.name}]({r.html_url}) | {r.language or '-'} | {r.stars:,} | {r.forks:,} |")

    return "\n".join(lines) + "\n"


def export_repo_to_json(analysis: RepoAnalysis) -> str:
    data = asdict(analysis)
    return json.dumps(data, indent=2, cls=DateTimeEncoder)


def export_repo_to_markdown(analysis: RepoAnalysis) -> str:
    r = analysis.repository
    lines = [
        f"# Repository Analysis: {r.full_name}",
        "",
        f"**Description:** {r.description or 'N/A'}  ",
        f"**URL:** {r.html_url}  ",
        f"**Default Branch:** {r.default_branch}  ",
        f"**License:** {r.license_name or 'None'}  ",
        f"**Health Score:** {analysis.health.health_score}/100  ",
        "",
        "## Key Statistics",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Stars | {r.stars:,} |",
        f"| Forks | {r.forks:,} |",
        f"| Watchers | {r.watchers:,} |",
        f"| Open Issues | {r.open_issues:,} |",
        f"| Size | {r.size_kb:,} KB |",
        "",
        "## Language Composition",
        "",
        "| Language | Percentage | Bytes |",
        "|---|---|---|",
    ]

    for lang in analysis.languages.languages:
        lines.append(f"| {lang.name} | {lang.percentage:.1f}% | {lang.bytes_count:,} |")

    lines.extend([
        "",
        "## Top Contributors",
        "",
        "| Contributor | Contributions |",
        "|---|---|",
    ])

    for c in analysis.contributors:
        lines.append(f"| [{c.login}]({c.html_url}) | {c.contributions:,} |")

    return "\n".join(lines) + "\n"


def save_export_file(content: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
