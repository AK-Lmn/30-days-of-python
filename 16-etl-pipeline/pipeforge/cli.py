import sys
from pathlib import Path
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from pipeforge.engine.yaml_parser import PipelineConfigParser
from pipeforge.engine.pipeline import ETLPipeline, PipelineError
from pipeforge.extractors.csv_extractor import CsvExtractor
from pipeforge.extractors.json_extractor import JsonExtractor
from pipeforge.loaders.csv_loader import CsvLoader
from pipeforge.loaders.json_loader import JsonLoader
from pipeforge.loaders.database_loader import DatabaseLoader
from pipeforge.storage.audit_store import AuditStore
from pipeforge.models.enums import ErrorStrategy, LoadMode
from pipeforge.samples.generator import SampleDataGenerator

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="pipeforge")
def main() -> None:
    pass


@main.command(name="run")
@click.option("--config", "-c", "config_file", type=click.Path(exists=True), help="Path to pipeline YAML configuration file.")
@click.option("--source", "-s", type=click.Path(exists=True), help="Quick source file path (CSV or JSON).")
@click.option("--dest", "-d", help="Quick destination path or database URL.")
@click.option("--strategy", type=click.Choice(["FAIL_FAST", "QUARANTINE", "SKIP"], case_sensitive=False), default="QUARANTINE", help="Error handling strategy.")
def run_command(config_file: str | None, source: str | None, dest: str | None, strategy: str) -> None:
    if config_file:
        try:
            pipeline = PipelineConfigParser.from_yaml_file(config_file)
        except Exception as e:
            console.print(f"[bold red]Configuration error:[/bold red] {e}")
            sys.exit(1)
    elif source and dest:
        src_path = Path(source)
        error_strategy = ErrorStrategy(strategy.upper())
        if src_path.suffix.lower() == ".csv":
            extractor = CsvExtractor(src_path)
        else:
            extractor = JsonExtractor(src_path)

        if dest.startswith("sqlite://") or dest.endswith(".db"):
            url = dest if dest.startswith("sqlite://") else f"sqlite:///{dest}"
            loader = DatabaseLoader(url, table_name="pipeline_output", mode=LoadMode.REPLACE)
        elif dest.endswith(".csv"):
            loader = CsvLoader(dest, mode=LoadMode.REPLACE)
        else:
            loader = JsonLoader(dest, mode=LoadMode.REPLACE)

        pipeline = ETLPipeline(
            name=f"quick_{src_path.stem}",
            extractor=extractor,
            loaders=[loader],
            error_strategy=error_strategy,
        )
    else:
        console.print("[bold yellow]Please specify either --config <file.yaml> or both --source and --dest.[/bold yellow]")
        sys.exit(1)

    console.print(Panel(f"[bold green]Starting Pipeline:[/bold green] [cyan]{pipeline.name}[/cyan]\n[bold]Run ID:[/bold] {pipeline.run_id}"))

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(f"Processing {pipeline.name}...", total=None)

        def on_progress(read: int, loaded: int) -> None:
            progress.update(task, description=f"Read {read} | Loaded {loaded} records")

        pipeline.progress_callback = on_progress

        try:
            metrics = pipeline.run()
        except PipelineError as pe:
            console.print(f"[bold red]Pipeline failed (FAIL_FAST):[/bold red] {pe}")
            sys.exit(1)
        except Exception as ex:
            console.print(f"[bold red]Unexpected error during pipeline run:[/bold red] {ex}")
            sys.exit(1)

    table = Table(title=f"Pipeline Execution Summary — {pipeline.name}")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta")

    table.add_row("Status", "[green]SUCCESS[/green]" if metrics.records_invalid == 0 else "[yellow]PARTIAL / QUARANTINED[/yellow]")
    table.add_row("Records Read", str(metrics.records_read))
    table.add_row("Records Valid", str(metrics.records_valid))
    table.add_row("Records Invalid", str(metrics.records_invalid))
    table.add_row("Records Transformed", str(metrics.records_transformed))
    table.add_row("Records Loaded", str(metrics.records_loaded))
    table.add_row("Records Quarantined", str(metrics.records_quarantined))
    table.add_row("Records Skipped", str(metrics.records_skipped))
    table.add_row("Duration", f"{metrics.duration_seconds:.3f} s")
    table.add_row("Throughput", f"{metrics.throughput_records_per_second} rec/s")

    console.print(table)


@main.command(name="inspect")
@click.option("--source", "-s", required=True, type=click.Path(exists=True), help="Path to data source file.")
@click.option("--rows", "-n", default=5, help="Number of preview rows.")
def inspect_command(source: str, rows: int) -> None:
    src_path = Path(source)
    if src_path.suffix.lower() == ".csv":
        extractor = CsvExtractor(src_path)
    else:
        extractor = JsonExtractor(src_path)

    sample_records = []
    total_count = 0
    null_counts: dict[str, int] = {}
    type_inferences: dict[str, set[str]] = {}

    for record in extractor.extract():
        total_count += 1
        if len(sample_records) < rows:
            sample_records.append(record.data)

        for col, val in record.data.items():
            if col not in null_counts:
                null_counts[col] = 0
                type_inferences[col] = set()
            if val is None or val == "":
                null_counts[col] += 1
            else:
                type_inferences[col].add(type(val).__name__)

    console.print(Panel(f"[bold cyan]Source Inspection:[/bold cyan] {source}\n[bold]Total Rows:[/bold] {total_count}"))

    stats_table = Table(title="Column Profiling")
    stats_table.add_column("Column", style="bold green")
    stats_table.add_column("Inferred Types", style="cyan")
    stats_table.add_column("Null Count", style="yellow")
    stats_table.add_column("Null %", style="red")

    for col in null_counts:
        n_nulls = null_counts[col]
        pct = (n_nulls / total_count * 100) if total_count > 0 else 0.0
        types_str = ", ".join(sorted(type_inferences[col])) if type_inferences[col] else "null"
        stats_table.add_row(col, types_str, str(n_nulls), f"{pct:.1f}%")

    console.print(stats_table)

    if sample_records:
        preview_table = Table(title=f"Sample Data (First {len(sample_records)} Rows)")
        for col in sample_records[0].keys():
            preview_table.add_column(str(col), style="white")
        for r in sample_records:
            preview_table.add_row(*[str(r.get(c, "")) for c in sample_records[0].keys()])
        console.print(preview_table)


@main.command(name="history")
@click.option("--limit", "-l", default=10, help="Number of past runs to display.")
@click.option("--db", default=None, help="Custom audit database URL.")
def history_command(limit: int, db: str | None) -> None:
    store = AuditStore(db)
    runs = store.list_runs(limit=limit)

    if not runs:
        console.print("[yellow]No pipeline execution history found.[/yellow]")
        return

    table = Table(title=f"Pipeline Execution History (Last {len(runs)})")
    table.add_column("Run ID", style="dim", no_wrap=True)
    table.add_column("Pipeline Name", style="bold cyan")
    table.add_column("Status", style="bold")
    table.add_column("Read", justify="right")
    table.add_column("Loaded", justify="right", style="green")
    table.add_column("Quarantined", justify="right", style="yellow")
    table.add_column("Duration", justify="right")
    table.add_column("Started At", style="dim")

    for r in runs:
        status_style = "green" if r.status == "SUCCESS" else ("yellow" if r.status == "PARTIAL" else "red")
        status_display = f"[{status_style}]{r.status}[/{status_style}]"
        duration_display = f"{r.duration_seconds:.2f}s" if r.duration_seconds is not None else "-"
        start_display = r.started_at.strftime("%Y-%m-%d %H:%M:%S") if r.started_at else "-"

        table.add_row(
            r.id[:8] + "...",
            r.pipeline_name,
            status_display,
            str(r.records_read),
            str(r.records_loaded),
            str(r.records_quarantined),
            duration_display,
            start_display,
        )

    console.print(table)


@main.group(name="quarantine")
def quarantine_group() -> None:
    pass


@quarantine_group.command(name="list")
@click.argument("run_id")
@click.option("--db", default=None, help="Custom audit database URL.")
def quarantine_list(run_id: str, db: str | None) -> None:
    store = AuditStore(db)
    runs = store.list_runs(limit=100)
    matched_run = next((r for r in runs if r.id.startswith(run_id)), None)
    if not matched_run:
        console.print(f"[bold red]Run not found:[/bold red] {run_id}")
        return

    records = store.get_quarantined_records(matched_run.id)
    if not records:
        console.print(f"[green]No quarantined records for run {matched_run.id}[/green]")
        return

    table = Table(title=f"Quarantined Records for Run {matched_run.id[:8]} ({len(records)} items)")
    table.add_column("Row Number", style="dim", justify="right")
    table.add_column("Errors", style="bold red")
    table.add_column("Raw Data", style="white")

    for r in records[:20]:
        table.add_row(str(r.row_number), r.errors, r.raw_data[:80] + ("..." if len(r.raw_data) > 80 else ""))

    console.print(table)
    if len(records) > 20:
        console.print(f"[dim]Showing 20 of {len(records)} records. Use 'quarantine export' to inspect all.[/dim]")


@quarantine_group.command(name="export")
@click.argument("run_id")
@click.option("--output", "-o", required=True, type=click.Path(), help="Output JSON file path.")
@click.option("--db", default=None, help="Custom audit database URL.")
def quarantine_export(run_id: str, output: str, db: str | None) -> None:
    store = AuditStore(db)
    runs = store.list_runs(limit=100)
    matched_run = next((r for r in runs if r.id.startswith(run_id)), None)
    if not matched_run:
        console.print(f"[bold red]Run not found:[/bold red] {run_id}")
        return

    count = store.export_quarantine_to_json(matched_run.id, output)
    console.print(f"[bold green]Successfully exported {count} quarantined records to:[/bold green] {output}")


@main.command(name="sample-data")
@click.option("--type", "-t", "sample_type", type=click.Choice(["orders", "users"], case_sensitive=False), default="orders")
@click.option("--output", "-o", default=None, help="Output file path (defaults to sample_<type>.<ext>).")
@click.option("--count", "-n", default=100, help="Number of records to generate.")
@click.option("--lines", is_flag=True, help="For JSON: output JSON Lines (.jsonl).")
def sample_data_command(sample_type: str, output: str | None, count: int, lines: bool) -> None:
    if sample_type == "orders":
        out_file = output or "sample_orders.csv"
        path = SampleDataGenerator.generate_orders_csv(out_file, count=count)
    else:
        out_file = output or ("sample_users.jsonl" if lines else "sample_users.json")
        path = SampleDataGenerator.generate_users_json(out_file, count=count, lines=lines)
    console.print(f"[bold green]Generated {count} {sample_type} records at:[/bold green] [cyan]{path}[/cyan]")


if __name__ == "__main__":
    main()
