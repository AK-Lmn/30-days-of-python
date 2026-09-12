import sys
from typing import Any, Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from devvault.models import VaultItem

console = Console()

TYPE_STYLES = {
    "snippet": ("SNIPPET", "bold cyan"),
    "command": ("COMMAND", "bold yellow"),
    "note": ("NOTE", "bold green"),
    "url": ("URL", "bold magenta"),
}


def get_type_badge(item_type: str) -> Text:
    label, style = TYPE_STYLES.get(item_type.lower(), (item_type.upper(), "white"))
    return Text(f" {label} ", style=f"bold white on {style.split()[-1]}")


def print_items_table(
    items: List[VaultItem],
    title: str = "DevVault Entries",
    show_preview: bool = True,
) -> None:
    if not items:
        console.print("[yellow]No entries found in vault.[/yellow]")
        return

    table = Table(
        title=f"[bold]{title}[/bold] ({len(items)} found)",
        title_justify="left",
        header_style="bold blue",
        show_lines=False,
        border_style="dim",
    )

    table.add_column("ID", justify="right", style="cyan", no_wrap=True)
    table.add_column("Type", justify="center", no_wrap=True)
    table.add_column("Title", style="bold white", max_width=35)
    if show_preview:
        table.add_column("Preview / Content", style="dim", max_width=60)
    table.add_column("Updated", style="dim", justify="right", no_wrap=True)

    for item in items:
        badge = get_type_badge(item.item_type)

        preview = item.content.strip().replace("\n", " ")
        if len(preview) > 57:
            preview = preview[:54] + "..."

        date_display = item.updated_at.split("T")[0] if "T" in item.updated_at else item.updated_at

        row_args = [
            str(item.id),
            badge,
            item.title,
        ]
        if show_preview:
            row_args.append(preview)
        row_args.append(date_display)

        table.add_row(*row_args)

    console.print(table)


def print_item_detail(item: VaultItem) -> None:
    header_parts = [
        f"[bold cyan]ID:[/] {item.id}",
        f"[bold]Type:[/] {item.item_type.upper()}",
    ]
    if item.language:
        header_parts.append(f"[bold]Lang:[/] {item.language}")
    header_parts.append(f"[dim]Updated: {item.updated_at}[/dim]")

    subtitle = " | ".join(header_parts)

    body_elements = []

    if item.description:
        body_elements.append(f"[italic dim]{item.description}[/italic dim]\n")

    if item.item_type == "snippet":
        syntax_lang = item.language or "text"
        syntax = Syntax(
            item.content,
            syntax_lang,
            theme="monokai",
            line_numbers=True,
            word_wrap=True,
        )
        console.print(
            Panel(
                syntax,
                title=f"[bold white]{item.title}[/bold white]",
                subtitle=subtitle,
                border_style="cyan",
                padding=(1, 2),
            )
        )
        return

    elif item.item_type == "command":
        cmd_text = Text()
        cmd_text.append("$ ", style="bold yellow")
        cmd_text.append(item.content, style="bold bright_white")
        console.print(
            Panel(
                cmd_text,
                title=f"[bold yellow]Command:[/] {item.title}",
                subtitle=subtitle,
                border_style="yellow",
                padding=(1, 2),
            )
        )
        return

    elif item.item_type == "url":
        url_text = Text()
        url_text.append("🔗 URL: ", style="bold magenta")
        url_text.append(item.content, style="underline link " + item.content)
        console.print(
            Panel(
                url_text,
                title=f"[bold magenta]Bookmark:[/] {item.title}",
                subtitle=subtitle,
                border_style="magenta",
                padding=(1, 2),
            )
        )
        return

    else:
        rendered_note = Markdown(item.content)
        console.print(
            Panel(
                rendered_note,
                title=f"[bold green]Note:[/] {item.title}",
                subtitle=subtitle,
                border_style="green",
                padding=(1, 2),
            )
        )


def print_stats(stats: Dict[str, Any]) -> None:
    table = Table(title="📊 DevVault Statistics", show_header=False, border_style="cyan")
    table.add_column("Metric", style="bold cyan")
    table.add_column("Value", style="bold white")

    table.add_row("Total Entries", str(stats["total_items"]))

    by_type = stats.get("by_type", {})
    type_breakdown = ", ".join(f"{k.capitalize()}: {v}" for k, v in sorted(by_type.items())) or "None"
    table.add_row("Items by Type", type_breakdown)

    table.add_row("Last Activity", str(stats["last_updated"]))
    table.add_row("Vault Database", str(stats["db_path"]))

    console.print(table)
