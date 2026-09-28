from pathlib import Path
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from cleanforge.config import get_preset_recipe, load_recipe_file, save_recipe_file
from cleanforge.engine.builder import CleanBuilder
from cleanforge.engine.pipeline import CleanEngine
from cleanforge.io.reader import DatasetReader
from cleanforge.io.writer import DatasetWriter
from cleanforge.profiler.analyzer import DataProfiler
from cleanforge.samples.generator import generate_dirty_dataset

console = Console()


def format_health_score(score: float) -> str:
    if score >= 85.0:
        return f"[bold green]{score:.1f}%[/bold green]"
    if score >= 65.0:
        return f"[bold yellow]{score:.1f}%[/bold yellow]"
    return f"[bold red]{score:.1f}%[/bold red]"


@click.group()
def main() -> None:
    pass


@main.command()
@click.argument("file_path", type=click.Path(exists=True, path_type=Path))
@click.option("--delimiter", "-d", help="Custom CSV delimiter")
@click.option("--encoding", "-e", help="File character encoding")
def inspect(file_path: Path, delimiter: str | None, encoding: str | None) -> None:
    reader = DatasetReader()
    records = reader.read(file_path, delimiter=delimiter, encoding=encoding)
    profiler = DataProfiler()
    profile = profiler.profile(records)

    console.print()
    console.print(
        Panel.fit(
            f"[bold cyan]Dataset Profile:[/bold cyan] {file_path.name}\n"
            f"[bold]Total Rows:[/bold] {profile.row_count:,}   "
            f"[bold]Total Columns:[/bold] {profile.column_count}   "
            f"[bold]Duplicate Rows:[/bold] {profile.duplicate_rows:,}\n"
            f"[bold]Health Score:[/bold] {format_health_score(profile.health_score)}",
            title="CleanForge Inspector",
            border_style="cyan",
        )
    )

    table = Table(title="Column Profile & Diagnostics", border_style="cyan")
    table.add_column("Column", style="bold white")
    table.add_column("Type", style="cyan")
    table.add_column("Nulls", justify="right")
    table.add_column("Unique", justify="right")
    table.add_column("Whitespace Issues", justify="right")
    table.add_column("Min / Max", justify="left")
    table.add_column("Mean / Mode", justify="left")

    for col_name, col in profile.columns.items():
        null_str = f"{col.null_count} ({col.null_percentage:.1f}%)"
        unique_str = f"{col.unique_count} ({col.unique_percentage:.1f}%)"
        ws_str = str(col.whitespace_issues) if col.whitespace_issues > 0 else "-"

        min_max_parts = []
        if col.min_value is not None:
            min_max_parts.append(f"{str(col.min_value)[:12]}")
        if col.max_value is not None:
            min_max_parts.append(f"{str(col.max_value)[:12]}")
        min_max_str = " .. ".join(min_max_parts) or "-"

        mean_mode_parts = []
        if col.mean is not None:
            mean_mode_parts.append(f"mean:{col.mean:.2f}")
        if col.mode is not None:
            mean_mode_parts.append(f"mode:{str(col.mode)[:12]}")
        mean_mode_str = " | ".join(mean_mode_parts) or "-"

        table.add_row(
            col_name,
            col.inferred_type.value,
            null_str,
            unique_str,
            ws_str,
            min_max_str,
            mean_mode_str,
        )

    console.print(table)
    console.print()


@main.command()
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    "output_path",
    required=True,
    type=click.Path(path_type=Path),
    help="Destination path for cleaned dataset",
)
@click.option(
    "--recipe",
    "-r",
    "recipe_path",
    type=click.Path(exists=True, path_type=Path),
    help="Path to YAML or JSON recipe",
)
@click.option(
    "--preset",
    "-p",
    type=click.Choice(["standard", "customer", "ecommerce"]),
    help="Built-in recipe preset to use",
)
@click.option(
    "--quarantine",
    "-q",
    "quarantine_path",
    type=click.Path(path_type=Path),
    help="Path to save quarantined rows",
)
@click.option(
    "--report",
    "report_path",
    type=click.Path(path_type=Path),
    help="Path to save audit report (.md or .json)",
)
def clean(
    input_path: Path,
    output_path: Path,
    recipe_path: Path | None,
    preset: str | None,
    quarantine_path: Path | None,
    report_path: Path | None,
) -> None:
    if recipe_path:
        recipe = load_recipe_file(recipe_path)
    elif preset:
        recipe = get_preset_recipe(preset)
    else:
        recipe = get_preset_recipe("standard")

    builder = CleanBuilder()
    builder.load(input_path)
    builder.apply_recipe(recipe)

    report = builder.save(
        output_path=output_path,
        quarantine_path=quarantine_path,
        report_path=report_path,
    )

    console.print()
    console.print(
        Panel.fit(
            f"[bold green]Cleaning Completed Successfully![/bold green]\n"
            f"[bold]Input File:[/bold] {input_path.name}  ->  [bold]Output File:[/bold] {output_path.name}\n"
            f"[bold]Initial Rows:[/bold] {report.initial_rows:,}   "
            f"[bold]Final Clean Rows:[/bold] {report.final_rows:,}   "
            f"[bold]Quarantined:[/bold] {report.quarantined_rows:,}\n"
            f"[bold]Initial Health:[/bold] {format_health_score(report.initial_health_score)}   "
            f"[bold]Final Health:[/bold] {format_health_score(report.final_health_score)}   "
            f"[bold]Score Delta:[/bold] +{max(0.0, report.final_health_score - report.initial_health_score):.1f}%\n"
            f"[bold]Execution Time:[/bold] {report.execution_time_ms:.2f} ms",
            title="CleanForge Engine",
            border_style="green",
        )
    )

    if report.modifications_by_column:
        mod_table = Table(title="Column Cleaning Metrics", border_style="green")
        mod_table.add_column("Column", style="bold white")
        mod_table.add_column("Modified Values", justify="right", style="green")
        for col, count in sorted(report.modifications_by_column.items()):
            mod_table.add_row(col, f"{count:,}")
        console.print(mod_table)

    if report.quarantined_reasons:
        q_table = Table(title="Quarantine Diagnostics", border_style="red")
        q_table.add_column("Reason", style="bold white")
        q_table.add_column("Violated Rows", justify="right", style="red")
        for reason, count in sorted(report.quarantined_reasons.items()):
            q_table.add_row(reason, f"{count:,}")
        console.print(q_table)

    console.print()


@main.command()
@click.argument("before_path", type=click.Path(exists=True, path_type=Path))
@click.argument("after_path", type=click.Path(exists=True, path_type=Path))
def diff(before_path: Path, after_path: Path) -> None:
    reader = DatasetReader()
    profiler = DataProfiler()

    before_data = reader.read(before_path)
    after_data = reader.read(after_path)

    before_prof = profiler.profile(before_data)
    after_prof = profiler.profile(after_data)

    console.print()
    diff_table = Table(title="Before vs After Quality Comparison", border_style="magenta")
    diff_table.add_column("Metric", style="bold white")
    diff_table.add_column(f"Before ({before_path.name})", justify="right")
    diff_table.add_column(f"After ({after_path.name})", justify="right")
    diff_table.add_column("Delta", justify="right", style="bold")

    row_delta = after_prof.row_count - before_prof.row_count
    diff_table.add_row(
        "Total Rows",
        f"{before_prof.row_count:,}",
        f"{after_prof.row_count:,}",
        f"{row_delta:+,}",
    )

    dup_delta = after_prof.duplicate_rows - before_prof.duplicate_rows
    diff_table.add_row(
        "Duplicate Rows",
        f"{before_prof.duplicate_rows:,}",
        f"{after_prof.duplicate_rows:,}",
        f"{dup_delta:+,}",
    )

    score_delta = after_prof.health_score - before_prof.health_score
    diff_table.add_row(
        "Health Score",
        f"{before_prof.health_score:.1f}%",
        f"{after_prof.health_score:.1f}%",
        f"{score_delta:+.1f}%",
    )

    console.print(diff_table)
    console.print()


@main.command()
@click.option("--rows", "-n", default=50, help="Number of records to generate")
@click.option(
    "--output",
    "-o",
    "output_path",
    type=click.Path(path_type=Path),
    default=Path("dirty_sample.csv"),
    help="Target file path",
)
def sample(rows: int, output_path: Path) -> None:
    dataset = generate_dirty_dataset(row_count=rows)
    writer = DatasetWriter()
    writer.write(dataset, output_path)
    console.print(
        f"[green]Generated {len(dataset)} dirty sample records -> {output_path}[/green]"
    )


@main.command(name="recipe-init")
@click.option(
    "--preset",
    "-p",
    type=click.Choice(["standard", "customer", "ecommerce"]),
    default="customer",
    help="Starter preset to generate",
)
@click.option(
    "--output",
    "-o",
    "output_path",
    type=click.Path(path_type=Path),
    default=Path("recipe.yaml"),
    help="Output recipe path (.yaml or .json)",
)
def recipe_init(preset: str, output_path: Path) -> None:
    recipe = get_preset_recipe(preset)
    save_recipe_file(recipe, output_path)
    console.print(
        f"[green]Created recipe template '{preset}' -> {output_path}[/green]"
    )


if __name__ == "__main__":
    main()
