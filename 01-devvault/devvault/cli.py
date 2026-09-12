import json
import os
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Optional

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

import click
import pyperclip
from rich.prompt import Confirm, Prompt

from devvault import __version__
from devvault.config import get_db_path
from devvault.db import Database
from devvault.models import VALID_ITEM_TYPES, VaultItem
from devvault.views import (
    console,
    print_item_detail,
    print_items_table,
    print_stats,
)


def safe_copy_to_clipboard(content: str) -> bool:
    try:
        pyperclip.copy(content)
        return True
    except Exception as e:
        console.print(f"[dim yellow]Warning: Could not access clipboard ({e}).[/dim yellow]")
        return False


@click.group()
@click.option("--db", "db_override", type=click.Path(), help="Path to custom SQLite vault database.")
@click.version_option(version=__version__, prog_name="devvault")
@click.pass_context
def cli(ctx: click.Context, db_override: Optional[str]) -> None:
    ctx.ensure_object(dict)
    db_path = get_db_path(db_override)
    ctx.obj["db"] = Database(db_path)


@cli.command("add")
@click.option("-t", "--title", help="Title of the entry.")
@click.option(
    "-T",
    "--type",
    "item_type",
    type=click.Choice(sorted(list(VALID_ITEM_TYPES)), case_sensitive=False),
    help="Type of entry: snippet, command, note, or url.",
)
@click.option("-c", "--content", help="Content or code of the entry.")
@click.option("-l", "--language", help="Syntax language (for snippets, e.g. python, bash).")
@click.option("-d", "--desc", "--description", "description", help="Description or usage notes.")
@click.option("--stdin", is_flag=True, help="Read content from standard input.")
@click.option("-e", "--editor", is_flag=True, help="Open default text editor to write content.")
@click.pass_context
def add_item(
    ctx: click.Context,
    title: Optional[str],
    item_type: Optional[str],
    content: Optional[str],
    language: Optional[str],
    description: Optional[str],
    stdin: bool,
    editor: bool,
) -> None:
    db: Database = ctx.obj["db"]

    if stdin or (not sys.stdin.isatty() and content is None):
        content = sys.stdin.read().strip()

    if not title:
        title = Prompt.ask("[bold cyan]Enter title[/bold cyan]").strip()
        if not title:
            console.print("[red]Error: Title cannot be empty.[/red]")
            sys.exit(1)

    if not item_type:
        item_type = Prompt.ask(
            "[bold cyan]Select type[/bold cyan]",
            choices=sorted(list(VALID_ITEM_TYPES)),
            default="snippet",
        )

    if editor:
        initial_marker = f"# Write your {item_type} below. Save and close your editor.\n"
        edited = click.edit(initial_marker)
        if edited:
            content = edited.replace(initial_marker, "").strip()
        else:
            console.print("[yellow]No content saved from editor.[/yellow]")
            return

    if content is None:
        if item_type == "command":
            content = Prompt.ask("[bold cyan]Enter command[/bold cyan]").strip()
        elif item_type == "url":
            content = Prompt.ask("[bold cyan]Enter URL[/bold cyan]").strip()
        else:
            use_editor = Confirm.ask("Open editor for multi-line content?", default=False)
            if use_editor:
                edited = click.edit()
                content = edited.strip() if edited else ""
            else:
                content = Prompt.ask(f"[bold cyan]Enter {item_type} content[/bold cyan]").strip()

    if not content:
        console.print("[red]Error: Content cannot be empty.[/red]")
        sys.exit(1)

    if item_type == "snippet" and not language:
        suggested_lang = "python"
        lang_input = Prompt.ask("[bold cyan]Syntax language (e.g. python, bash, sql)[/bold cyan]", default=suggested_lang)
        language = lang_input.strip()

    item = VaultItem(
        title=title,
        item_type=item_type,
        content=content,
        language=language,
        description=description,
    )

    created = db.add_item(item)
    console.print(f"[bold green]✓[/bold green] Saved {created.item_type} [bold cyan]#{created.id}[/bold cyan]: [white]{created.title}[/white]")


@cli.group("snippet")
def snippet_group() -> None:
    pass


@snippet_group.command("add")
@click.argument("title")
@click.option("-c", "--content", help="Snippet code.")
@click.option("-l", "--language", default="python", help="Language for syntax highlighting.")
@click.option("-d", "--desc", help="Description.")
@click.option("-e", "--editor", is_flag=True, help="Open editor to write code.")
@click.pass_context
def add_snippet(
    ctx: click.Context,
    title: str,
    content: Optional[str],
    language: str,
    desc: Optional[str],
    editor: bool,
) -> None:
    ctx.invoke(
        add_item,
        title=title,
        item_type="snippet",
        content=content,
        language=language,
        description=desc,
        editor=editor,
    )


@cli.group("cmd")
def cmd_group() -> None:
    pass


@cmd_group.command("add")
@click.argument("title")
@click.argument("command_text", required=False)
@click.option("-d", "--desc", help="Description.")
@click.pass_context
def add_cmd(
    ctx: click.Context,
    title: str,
    command_text: Optional[str],
    desc: Optional[str],
) -> None:
    ctx.invoke(
        add_item,
        title=title,
        item_type="command",
        content=command_text,
        language="bash",
        description=desc,
    )


@cli.group("note")
def note_group() -> None:
    pass


@note_group.command("add")
@click.argument("title")
@click.argument("note_text", required=False)
@click.option("-d", "--desc", help="Description.")
@click.option("-e", "--editor", is_flag=True, help="Open editor to compose note.")
@click.pass_context
def add_note(
    ctx: click.Context,
    title: str,
    note_text: Optional[str],
    desc: Optional[str],
    editor: bool,
) -> None:
    ctx.invoke(
        add_item,
        title=title,
        item_type="note",
        content=note_text,
        description=desc,
        editor=editor,
    )


@cli.group("url")
def url_group() -> None:
    pass


@url_group.command("add")
@click.argument("title")
@click.argument("url_text", required=False)
@click.option("-d", "--desc", help="Description.")
@click.pass_context
def add_url(
    ctx: click.Context,
    title: str,
    url_text: Optional[str],
    desc: Optional[str],
) -> None:
    ctx.invoke(
        add_item,
        title=title,
        item_type="url",
        content=url_text,
        description=desc,
    )


@cli.command("list")
@click.option(
    "-t",
    "--type",
    "item_type",
    type=click.Choice(sorted(list(VALID_ITEM_TYPES)), case_sensitive=False),
    help="Filter by item type.",
)
@click.option("-n", "--limit", default=50, show_default=True, help="Maximum number of items to display.")
@click.pass_context
def list_items(ctx: click.Context, item_type: Optional[str], limit: int) -> None:
    db: Database = ctx.obj["db"]
    items = db.list_items(item_type=item_type, limit=limit)
    title = f"Vault Entries (type: {item_type})" if item_type else "Vault Entries"
    print_items_table(items, title=title)


@cli.command("search")
@click.argument("query")
@click.option(
    "-t",
    "--type",
    "item_type",
    type=click.Choice(sorted(list(VALID_ITEM_TYPES)), case_sensitive=False),
    help="Filter search by item type.",
)
@click.option("-n", "--limit", default=50, show_default=True, help="Maximum number of results.")
@click.pass_context
def search_items(ctx: click.Context, query: str, item_type: Optional[str], limit: int) -> None:
    db: Database = ctx.obj["db"]
    items = db.search_items(search_query=query, item_type=item_type, limit=limit)
    title = f"Search Results for '{query}'"
    print_items_table(items, title=title)


@cli.command("show")
@click.argument("item_id", type=int)
@click.option("-c", "--copy", is_flag=True, help="Also copy content to clipboard.")
@click.pass_context
def show_item(ctx: click.Context, item_id: int, copy: bool) -> None:
    db: Database = ctx.obj["db"]
    item = db.get_item(item_id)
    if not item:
        console.print(f"[red]Error: Item #{item_id} not found.[/red]")
        sys.exit(1)

    print_item_detail(item)
    if copy:
        if safe_copy_to_clipboard(item.content):
            console.print("[bold green]✓ Copied content to clipboard![/bold green]")


@cli.command("get")
@click.argument("item_id", type=int)
@click.option("-c", "--copy", is_flag=True, help="Also copy content to clipboard.")
@click.pass_context
def get_item(ctx: click.Context, item_id: int, copy: bool) -> None:
    ctx.invoke(show_item, item_id=item_id, copy=copy)


@cli.command("copy")
@click.argument("item_id", type=int)
@click.pass_context
def copy_item(ctx: click.Context, item_id: int) -> None:
    db: Database = ctx.obj["db"]
    item = db.get_item(item_id)
    if not item:
        console.print(f"[red]Error: Item #{item_id} not found.[/red]")
        sys.exit(1)

    if safe_copy_to_clipboard(item.content):
        console.print(f"[bold green]✓[/bold green] Copied [cyan]#{item.id}[/cyan] ([white]{item.title}[/white]) to clipboard!")


@cli.command("run")
@click.argument("item_id", type=int)
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompt before running command.")
@click.pass_context
def run_command(ctx: click.Context, item_id: int, yes: bool) -> None:
    db: Database = ctx.obj["db"]
    item = db.get_item(item_id)
    if not item:
        console.print(f"[red]Error: Item #{item_id} not found.[/red]")
        sys.exit(1)

    if item.item_type != "command":
        console.print(f"[yellow]Note: Item #{item_id} is a '{item.item_type}', not a 'command'.[/yellow]")

    console.print(f"[bold]Command to execute:[/] [bold yellow]{item.content}[/bold yellow]")

    if not yes:
        proceed = Confirm.ask("Are you sure you want to run this command in your shell?", default=True)
        if not proceed:
            console.print("[yellow]Aborted.[/yellow]")
            return

    console.print("[dim]Executing...[/dim]\n")
    try:
        res = subprocess.run(item.content, shell=True)
        if res.returncode != 0:
            console.print(f"\n[red]Command exited with return code {res.returncode}[/red]")
        else:
            console.print("\n[bold green]✓ Finished executing successfully.[/bold green]")
    except Exception as e:
        console.print(f"[red]Execution failed: {e}[/red]")


@cli.command("open")
@click.argument("item_id", type=int)
@click.pass_context
def open_url(ctx: click.Context, item_id: int) -> None:
    db: Database = ctx.obj["db"]
    item = db.get_item(item_id)
    if not item:
        console.print(f"[red]Error: Item #{item_id} not found.[/red]")
        sys.exit(1)

    url = item.content.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        url = "https://" + url

    console.print(f"[bold magenta]Opening URL:[/] {url}")
    webbrowser.open(url)


@cli.command("edit")
@click.argument("item_id", type=int)
@click.option("-t", "--title", help="New title.")
@click.option("-c", "--content", help="New content.")
@click.option("-l", "--language", help="New language.")
@click.option("-d", "--desc", help="New description.")
@click.option("-e", "--editor", is_flag=True, help="Open current content in editor.")
@click.pass_context
def edit_item(
    ctx: click.Context,
    item_id: int,
    title: Optional[str],
    content: Optional[str],
    language: Optional[str],
    desc: Optional[str],
    editor: bool,
) -> None:
    db: Database = ctx.obj["db"]
    item = db.get_item(item_id)
    if not item:
        console.print(f"[red]Error: Item #{item_id} not found.[/red]")
        sys.exit(1)

    if editor:
        edited = click.edit(item.content)
        if edited is not None:
            content = edited.strip()

    updates = {}
    if title is not None:
        updates["title"] = title
    if content is not None:
        updates["content"] = content
    if language is not None:
        updates["language"] = language
    if desc is not None:
        updates["description"] = desc

    if not updates and not editor:
        console.print("[yellow]No changes specified. Use flags (e.g. -t, -c, -d) or -e/--editor.[/yellow]")
        return

    updated = db.update_item(item_id, **updates)
    if updated:
        console.print(f"[bold green]✓[/bold green] Updated item [cyan]#{item_id}[/cyan]: [white]{updated.title}[/white]")


@cli.command("delete")
@click.argument("item_id", type=int)
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompt.")
@click.pass_context
def delete_item(ctx: click.Context, item_id: int, yes: bool) -> None:
    db: Database = ctx.obj["db"]
    item = db.get_item(item_id)
    if not item:
        console.print(f"[red]Error: Item #{item_id} not found.[/red]")
        sys.exit(1)

    if not yes:
        proceed = Confirm.ask(f"Are you sure you want to delete #{item.id} '{item.title}'?", default=False)
        if not proceed:
            console.print("[yellow]Aborted.[/yellow]")
            return

    if db.delete_item(item_id):
        console.print(f"[bold green]✓[/bold green] Deleted item [cyan]#{item_id}[/cyan] ({item.title})")
    else:
        console.print(f"[red]Failed to delete item #{item_id}.[/red]")


@cli.command("stats")
@click.pass_context
def show_stats(ctx: click.Context) -> None:
    db: Database = ctx.obj["db"]
    stats = db.get_vault_stats()
    print_stats(stats)


@cli.command("export")
@click.option(
    "-f",
    "--format",
    "export_format",
    type=click.Choice(["json", "markdown"], case_sensitive=False),
    default="json",
    show_default=True,
    help="Export format.",
)
@click.option("-o", "--output", type=click.Path(), help="File path to save the export to.")
@click.pass_context
def export_vault(ctx: click.Context, export_format: str, output: Optional[str]) -> None:
    db: Database = ctx.obj["db"]
    exported_text = db.export_all(format_type=export_format)

    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(exported_text, encoding="utf-8")
        console.print(f"[bold green]✓[/bold green] Exported vault entries to [cyan]{out_path.resolve()}[/cyan]")
    else:
        click.echo(exported_text)


@cli.command("import")
@click.argument("file_path", type=click.Path(exists=True))
@click.pass_context
def import_vault(ctx: click.Context, file_path: str) -> None:
    db: Database = ctx.obj["db"]
    src_path = Path(file_path)
    try:
        content = src_path.read_text(encoding="utf-8")
        data = json.loads(content)
        if not isinstance(data, list):
            console.print("[red]Error: Import file must contain a JSON list of items.[/red]")
            sys.exit(1)
        count = db.import_all(data)
        console.print(f"[bold green]✓[/bold green] Successfully imported [cyan]{count}[/cyan] items into the vault!")
    except Exception as e:
        console.print(f"[red]Import failed: {e}[/red]")
        sys.exit(1)


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
