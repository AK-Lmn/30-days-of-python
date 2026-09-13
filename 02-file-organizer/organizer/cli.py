import sys
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
from rich.prompt import Confirm
from organizer import __version__
from organizer.config import (
    generate_starter_config,
    get_history_db_path,
    load_config,
)
from organizer.core import (
    clean_empty_directories,
    execute_organization,
    execute_undo,
    plan_organization,
)
from organizer.duplicates import find_duplicates
from organizer.history import HistoryManager
from organizer.models import (
    ConflictResolution,
    OrganizeMode,
    OrganizeStrategy,
)
from organizer.views import (
    console,
    print_clean_empty_summary,
    print_duplicate_groups,
    print_organize_summary,
    print_preview_table,
    print_sessions_history,
    print_undo_summary,
)


@click.group()
@click.option("--db", "db_override", type=click.Path(), help="Path to custom SQLite history database.")
@click.version_option(version=__version__, prog_name="organizer")
@click.pass_context
def cli(ctx: click.Context, db_override: Optional[str]) -> None:
    ctx.ensure_object(dict)
    history_db = get_history_db_path(db_override)
    ctx.obj["history"] = HistoryManager(history_db)


@cli.command("organize")
@click.argument("directory", default=".", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path))
@click.option("-n", "--dry-run", is_flag=True, help="Simulate organization without moving any files.")
@click.option("-c", "--copy", "is_copy", is_flag=True, help="Copy files instead of moving them.")
@click.option("-r", "--recursive", is_flag=True, help="Scan subdirectories recursively.")
@click.option(
    "--by",
    "strategy_name",
    type=click.Choice(["category", "extension", "date", "size"], case_sensitive=False),
    default="category",
    help="Strategy used to sort files.",
)
@click.option(
    "--conflict",
    "conflict_name",
    type=click.Choice(["rename", "skip", "overwrite", "hash"], case_sensitive=False),
    default="rename",
    help="Strategy when destination file already exists.",
)
@click.option("--dest", "destination_dir", type=click.Path(file_okay=False, dir_okay=True, path_type=Path), default=None, help="Custom destination directory.")
@click.option("--date-subfolders", is_flag=True, help="Group files into Year/Month subfolders.")
@click.option("--hidden", "include_hidden", is_flag=True, help="Include hidden files and dotfiles.")
@click.option("--config", "config_file", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None, help="Custom configuration file.")
@click.pass_context
def organize_cmd(
    ctx: click.Context,
    directory: Path,
    dry_run: bool,
    is_copy: bool,
    recursive: bool,
    strategy_name: str,
    conflict_name: str,
    destination_dir: Optional[Path],
    date_subfolders: bool,
    include_hidden: bool,
    config_file: Optional[Path],
) -> None:
    config = load_config(config_file)
    strategy = OrganizeStrategy(strategy_name.lower())
    conflict = ConflictResolution(conflict_name.lower())
    mode = OrganizeMode.COPY if is_copy else OrganizeMode.MOVE
    history_mgr: HistoryManager = ctx.obj["history"]

    actions = plan_organization(
        source_dir=directory,
        strategy=strategy,
        config=config,
        mode=mode,
        recursive=recursive,
        include_hidden=include_hidden,
        date_subfolders=date_subfolders,
        conflict_resolution=conflict,
        destination_dir=destination_dir,
    )

    if not actions:
        console.print("[dim yellow]No eligible files found to organize.[/dim yellow]")
        return

    print_preview_table(actions=actions, source_dir=directory, dry_run=dry_run)

    result = execute_organization(
        actions=actions,
        mode=mode,
        dry_run=dry_run,
        source_dir=directory,
        strategy=strategy.value,
        history_manager=history_mgr,
    )

    print_organize_summary(result=result, dry_run=dry_run)


@cli.command("undo")
@click.argument("session_id", required=False, type=int)
@click.pass_context
def undo_cmd(ctx: click.Context, session_id: Optional[int]) -> None:
    history_mgr: HistoryManager = ctx.obj["history"]
    result = execute_undo(history_manager=history_mgr, session_id=session_id)

    if not result:
        console.print("[yellow]No active session found to undo.[/yellow]")
        return

    print_undo_summary(result)


@cli.command("history")
@click.option("-l", "--limit", default=20, help="Number of past sessions to display.")
@click.pass_context
def history_cmd(ctx: click.Context, limit: int) -> None:
    history_mgr: HistoryManager = ctx.obj["history"]
    sessions = history_mgr.list_sessions(limit=limit)
    print_sessions_history(sessions)


@cli.command("duplicates")
@click.argument("directory", default=".", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path))
@click.option("-r/--no-recursive", default=True, help="Scan recursively or shallowly.")
@click.option("--min-size", default=0, help="Minimum file size in bytes to check.")
@click.option("--delete", is_flag=True, help="Delete duplicate files after confirmation.")
@click.option("--move-to", "move_dest", type=click.Path(file_okay=False, dir_okay=True, path_type=Path), default=None, help="Move duplicate files into a target directory.")
def duplicates_cmd(
    directory: Path,
    r: bool,
    min_size: int,
    delete: bool,
    move_dest: Optional[Path],
) -> None:
    groups = find_duplicates(directory=directory, recursive=r, min_size=min_size)
    print_duplicate_groups(groups=groups, base_dir=directory)

    if not groups:
        return

    all_duplicates = [dup for g in groups for dup in g.duplicates]

    if move_dest:
        move_dest.mkdir(parents=True, exist_ok=True)
        if Confirm.ask(f"Move {len(all_duplicates)} duplicate files to [cyan]{move_dest}[/cyan]?"):
            moved_count = 0
            for dup in all_duplicates:
                try:
                    target = move_dest / dup.name
                    counter = 1
                    while target.exists():
                        target = move_dest / f"{dup.stem} ({counter}){dup.suffix}"
                        counter += 1
                    dup.rename(target)
                    moved_count += 1
                except OSError as e:
                    console.print(f"[red]Error moving {dup}: {e}[/red]")
            console.print(f"[green]Successfully moved {moved_count} duplicate files.[/green]")
        return

    if delete:
        if Confirm.ask(f"[bold red]Permanently delete {len(all_duplicates)} duplicate files?[/bold red]"):
            deleted_count = 0
            for dup in all_duplicates:
                try:
                    dup.unlink()
                    deleted_count += 1
                except OSError as e:
                    console.print(f"[red]Error deleting {dup}: {e}[/red]")
            console.print(f"[green]Successfully deleted {deleted_count} duplicate files.[/green]")


@cli.command("clean-empty")
@click.argument("directory", default=".", type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path))
@click.option("-n", "--dry-run", is_flag=True, help="Preview empty directories without deleting.")
def clean_empty_cmd(directory: Path, dry_run: bool) -> None:
    removed = clean_empty_directories(directory=directory, dry_run=dry_run)
    print_clean_empty_summary(directories=removed, dry_run=dry_run)


@cli.group("config")
def config_group() -> None:
    pass


@config_group.command("init")
@click.option("-p", "--path", default="organizer.yaml", type=click.Path(dir_okay=False, path_type=Path), help="Output path for config file.")
@click.option("-f", "--force", is_flag=True, help="Overwrite existing configuration file.")
def config_init_cmd(path: Path, force: bool) -> None:
    if path.exists() and not force:
        console.print(f"[yellow]Configuration file already exists at {path}. Use --force to overwrite.[/yellow]")
        return

    starter = generate_starter_config()
    path.write_text(starter, encoding="utf-8")
    console.print(f"[green]Starter configuration generated at [bold]{path}[/bold]![/green]")


@config_group.command("show")
@click.option("-c", "--config", "config_file", type=click.Path(exists=True, dir_okay=False, path_type=Path), default=None, help="Configuration file to inspect.")
def config_show_cmd(config_file: Optional[Path]) -> None:
    cfg = load_config(config_file)
    console.print("[bold cyan]Active File Categories:[/bold cyan]")
    for category, exts in cfg.categories.items():
        console.print(f"  [magenta]{category}[/magenta]: {', '.join(exts)}")

    if cfg.rules:
        console.print("\n[bold cyan]Custom Rules:[/bold cyan]")
        for rule in cfg.rules:
            details = [f"folder: {rule.folder}"]
            if rule.extensions:
                details.append(f"exts: {', '.join(rule.extensions)}")
            if rule.pattern:
                details.append(f"pattern: {rule.pattern}")
            console.print(f"  [green]{rule.name}[/green] -> ({', '.join(details)})")


def main() -> None:
    cli(obj={})


if __name__ == "__main__":
    main()
