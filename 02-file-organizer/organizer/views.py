from pathlib import Path
from typing import Any
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from organizer.models import (
    DuplicateGroup,
    OrganizeAction,
    OrganizeResult,
    UndoResult,
)

console = Console()


def format_bytes(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    for unit in ["KB", "MB", "GB", "TB"]:
        size_bytes /= 1024.0
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
    return f"{size_bytes:.1f} PB"


def print_preview_table(
    actions: list[OrganizeAction],
    source_dir: Path,
    dry_run: bool = True,
) -> None:
    title = "[bold cyan]Dry-Run Plan (No changes made)[/bold cyan]" if dry_run else "[bold green]Executing Organization Plan[/bold green]"
    table = Table(title=title, show_lines=True, expand=True)
    table.add_column("Action", style="bold", width=8)
    table.add_column("Category", style="magenta", width=14)
    table.add_column("Source File", style="blue")
    table.add_column("Destination", style="cyan")
    table.add_column("Size", justify="right", width=10)
    table.add_column("Notes", style="dim")

    source_resolved = source_dir.resolve()

    for act in actions:
        try:
            rel_src = act.source_path.resolve().relative_to(source_resolved)
        except ValueError:
            rel_src = act.source_path

        try:
            rel_dest = act.destination_path.resolve().relative_to(source_resolved)
        except ValueError:
            rel_dest = act.destination_path

        if act.action_type == "move":
            action_text = Text("MOVE", style="bold green")
        elif act.action_type == "copy":
            action_text = Text("COPY", style="bold yellow")
        else:
            action_text = Text("SKIP", style="dim red")

        table.add_row(
            action_text,
            act.category,
            str(rel_src),
            str(rel_dest),
            format_bytes(act.size),
            act.reason or "",
        )

    console.print(table)


def print_organize_summary(result: OrganizeResult, dry_run: bool = False) -> None:
    lines = [
        f"[bold]Total Files Scanned:[/] {result.total_files_scanned}",
        f"[bold green]Files Moved:[/] {result.moved_count}",
        f"[bold yellow]Files Copied:[/] {result.copied_count}",
        f"[bold red]Files Skipped:[/] {result.skipped_count}",
        f"[bold cyan]Total Data Processed:[/] {format_bytes(result.bytes_processed)}",
    ]

    if result.session_id:
        lines.append(f"[bold magenta]Session ID:[/] #{result.session_id} (run `organizer undo` to revert)")

    title = "Dry-Run Summary" if dry_run else "Organization Summary"
    border_style = "cyan" if dry_run else "green"
    console.print(
        Panel(
            "\n".join(lines),
            title=f"[bold]{title}[/bold]",
            border_style=border_style,
            expand=False,
        )
    )


def print_duplicate_groups(groups: list[DuplicateGroup], base_dir: Path) -> None:
    if not groups:
        console.print("[green]No duplicate files detected![/green]")
        return

    total_wasted = sum(g.size * len(g.duplicates) for g in groups)
    table = Table(
        title=f"[bold red]Duplicate Files Found ({len(groups)} sets, {format_bytes(total_wasted)} reclaimable)[/bold red]",
        show_lines=True,
        expand=True,
    )
    table.add_column("Set", justify="center", width=5)
    table.add_column("Type", style="bold", width=12)
    table.add_column("File Path", style="blue")
    table.add_column("Size", justify="right", width=10)
    table.add_column("Checksum (SHA-256)", style="dim", width=18)

    base_resolved = base_dir.resolve()
    for idx, group in enumerate(groups, 1):
        try:
            orig_rel = group.original.resolve().relative_to(base_resolved)
        except ValueError:
            orig_rel = group.original

        table.add_row(
            str(idx),
            "[green]Original[/green]",
            str(orig_rel),
            format_bytes(group.size),
            group.checksum[:16] + "...",
        )

        for dup in group.duplicates:
            try:
                dup_rel = dup.resolve().relative_to(base_resolved)
            except ValueError:
                dup_rel = dup

            table.add_row(
                "",
                "[yellow]Duplicate[/yellow]",
                str(dup_rel),
                format_bytes(group.size),
                group.checksum[:16] + "...",
            )

    console.print(table)


def print_sessions_history(sessions: list[dict[str, Any]]) -> None:
    if not sessions:
        console.print("[dim]No organization history recorded yet.[/dim]")
        return

    table = Table(title="[bold cyan]Organization History[/bold cyan]", show_lines=True)
    table.add_column("ID", justify="right", width=5)
    table.add_column("Timestamp", style="blue")
    table.add_column("Source Directory", style="dim")
    table.add_column("Strategy", style="magenta")
    table.add_column("Actions", justify="right", width=8)
    table.add_column("Status", width=10)

    for s in sessions:
        status = "[dim]Undone[/dim]" if s.get("undone") else "[green]Active[/green]"
        table.add_row(
            str(s["id"]),
            str(s["timestamp"])[:19].replace("T", " "),
            str(s["source_directory"]),
            str(s["strategy"]),
            str(s["action_count"]),
            status,
        )

    console.print(table)


def print_undo_summary(result: UndoResult) -> None:
    lines = [
        f"[bold magenta]Session Restored:[/] #{result.session_id}",
        f"[bold green]Files Restored:[/] {result.restored_count}",
        f"[bold red]Files Failed:[/] {result.failed_count}",
        f"[bold cyan]Empty Folders Cleaned:[/] {len(result.cleaned_directories)}",
    ]
    console.print(
        Panel(
            "\n".join(lines),
            title="[bold green]Rollback Successful[/bold green]",
            border_style="green",
            expand=False,
        )
    )


def print_clean_empty_summary(directories: list[Path], dry_run: bool = False) -> None:
    if not directories:
        console.print("[dim]No empty directories found.[/dim]")
        return

    title = "[cyan]Dry-Run: Empty Folders to Remove[/cyan]" if dry_run else "[green]Removed Empty Folders[/green]"
    table = Table(title=title)
    table.add_column("#", justify="right", width=4)
    table.add_column("Directory Path", style="dim")

    for i, d in enumerate(directories, 1):
        table.add_row(str(i), str(d))

    console.print(table)
    total_text = f"Total empty folders: {len(directories)}"
    console.print(f"[bold]{total_text}[/bold]")
