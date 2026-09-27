import asyncio
import json
from datetime import timedelta
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import uvicorn

from taskforge.config import get_settings
from taskforge.core.enums import JobStatus, Priority
from taskforge.core.registry import registry
from taskforge.core.scheduler import Scheduler
from taskforge.core.worker import Worker
from taskforge.database import async_session_factory, init_db
from taskforge.models.db_models import utc_now
from taskforge.repositories.job_repo import JobRepository
import taskforge.tasks.builtins

console = Console()


@click.group()
def main() -> None:
    pass


@main.command("init-db")
def init_db_cmd() -> None:
    asyncio.run(init_db())
    console.print("[green]Database schema initialized successfully.[/green]")


@main.command("server")
@click.option("--host", default=None, help="Host interface to bind to")
@click.option("--port", default=None, type=int, help="Port to listen on")
@click.option("--reload", is_flag=True, default=False, help="Enable auto-reload")
def server_cmd(host: str | None, port: int | None, reload: bool) -> None:
    settings = get_settings()
    target_host = host or settings.host
    target_port = port or settings.port
    console.print(
        f"[bold cyan]Starting TaskForge REST API on http://{target_host}:{target_port}[/bold cyan]"
    )
    uvicorn.run(
        "taskforge.main:app",
        host=target_host,
        port=target_port,
        reload=reload,
    )


@main.command("worker")
@click.option("-q", "--queue", "queues", multiple=True, help="Queue(s) to process")
@click.option("-c", "--concurrency", default=2, type=int, help="Number of concurrent tasks")
@click.option("--worker-id", default=None, help="Custom identifier for the worker")
def worker_cmd(queues: tuple[str, ...], concurrency: int, worker_id: str | None) -> None:
    async def run_worker() -> None:
        await init_db()
        queue_list = list(queues) if queues else ["default"]
        worker = Worker(
            worker_id=worker_id,
            queues=queue_list,
            concurrency=concurrency,
        )
        console.print(
            Panel.fit(
                f"[bold green]Worker Online[/bold green]\n"
                f"Worker ID: [cyan]{worker.worker_id}[/cyan]\n"
                f"Queues: [yellow]{', '.join(queue_list)}[/yellow]\n"
                f"Concurrency: [magenta]{concurrency}[/magenta]",
                title="TaskForge Worker Engine",
            )
        )
        try:
            await worker.start()
        except (KeyboardInterrupt, asyncio.CancelledError):
            console.print("\n[yellow]Stopping worker...[/yellow]")
            await worker.stop()
            console.print("[green]Worker stopped safely.[/green]")

    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        pass


@main.command("scheduler")
@click.option("--poll-interval", default=1.0, type=float, help="Poll interval in seconds")
def scheduler_cmd(poll_interval: float) -> None:
    async def run_scheduler() -> None:
        await init_db()
        scheduler = Scheduler(poll_interval=poll_interval)
        console.print(
            Panel.fit(
                f"[bold cyan]TaskForge Scheduler Active[/bold cyan]\n"
                f"Interval: [yellow]{poll_interval}s[/yellow]",
                title="Cron & Delayed Scheduler",
            )
        )
        try:
            await scheduler.start()
        except (KeyboardInterrupt, asyncio.CancelledError):
            console.print("\n[yellow]Stopping scheduler...[/yellow]")
            await scheduler.stop()
            console.print("[green]Scheduler stopped safely.[/green]")

    try:
        asyncio.run(run_scheduler())
    except KeyboardInterrupt:
        pass


@main.command("enqueue")
@click.argument("task_name")
@click.option("-p", "--payload", default="{}", help="JSON payload string")
@click.option("-q", "--queue", default="default", help="Queue name")
@click.option("--priority", default=5, type=int, help="Priority (1-20)")
@click.option("--delay", default=0.0, type=float, help="Delay in seconds before execution")
@click.option("--max-retries", default=3, type=int, help="Maximum retry attempts")
def enqueue_cmd(
    task_name: str,
    payload: str,
    queue: str,
    priority: int,
    delay: float,
    max_retries: int,
) -> None:
    async def do_enqueue() -> None:
        await init_db()
        if not registry.has_task(task_name):
            console.print(f"[red]Error: Task '{task_name}' is not registered.[/red]")
            console.print(f"Registered tasks: {', '.join(registry.list_tasks())}")
            return

        try:
            parsed_payload = json.loads(payload)
        except json.JSONDecodeError as err:
            console.print(f"[red]Invalid JSON payload: {err}[/red]")
            return

        scheduled_at = None
        if delay > 0:
            scheduled_at = utc_now() + timedelta(seconds=delay)

        async with async_session_factory() as session:
            repo = JobRepository(session)
            job = await repo.create_job(
                task_name=task_name,
                payload=parsed_payload,
                queue=queue,
                priority=priority,
                scheduled_at=scheduled_at,
                max_retries=max_retries,
            )
            console.print(
                Panel.fit(
                    f"Job ID: [green]{job.id}[/green]\n"
                    f"Task: [cyan]{job.task_name}[/cyan]\n"
                    f"Queue: [yellow]{job.queue}[/yellow]\n"
                    f"Priority: [magenta]{job.priority}[/magenta]\n"
                    f"Status: [bold]{job.status}[/bold]\n"
                    f"Scheduled At: {job.scheduled_at.isoformat()}",
                    title="Job Enqueued",
                )
            )

    asyncio.run(do_enqueue())


@main.command("status")
@click.argument("job_id")
def status_cmd(job_id: str) -> None:
    async def get_status() -> None:
        await init_db()
        async with async_session_factory() as session:
            repo = JobRepository(session)
            job = await repo.get_job(job_id)
            if not job:
                console.print(f"[red]Job '{job_id}' not found.[/red]")
                return

            status_colors = {
                "pending": "yellow",
                "scheduled": "blue",
                "running": "cyan",
                "completed": "green",
                "failed": "red",
                "retrying": "magenta",
                "cancelled": "dim",
                "dead_letter": "bold red",
            }
            color = status_colors.get(job.status, "white")
            status_text = f"[{color}]{job.status.upper()}[/{color}]"

            table = Table(title=f"Job Details: {job.id}")
            table.add_column("Property", style="bold")
            table.add_column("Value")

            table.add_row("Task Name", job.task_name)
            table.add_row("Queue", job.queue)
            table.add_row("Status", status_text)
            table.add_row("Progress", f"{job.progress:.1f}% ({job.progress_message or 'N/A'})")
            table.add_row("Priority", str(job.priority))
            table.add_row("Retry Count", f"{job.retry_count}/{job.max_retries}")
            table.add_row("Worker ID", job.worker_id or "Unassigned")
            table.add_row("Payload", json.dumps(job.payload))
            table.add_row("Result", json.dumps(job.result) if job.result else "None")
            table.add_row("Error", job.error or "None")
            table.add_row("Created At", job.created_at.isoformat())
            table.add_row("Started At", job.started_at.isoformat() if job.started_at else "Not started")
            table.add_row("Completed At", job.completed_at.isoformat() if job.completed_at else "Incomplete")

            console.print(table)

    asyncio.run(get_status())


@main.command("list")
@click.option("-q", "--queue", default=None, help="Filter by queue")
@click.option("-s", "--status", default=None, type=click.Choice([s.value for s in JobStatus]), help="Filter by status")
@click.option("-t", "--task", default=None, help="Filter by task name")
@click.option("-l", "--limit", default=20, type=int, help="Limit number of jobs displayed")
def list_cmd(queue: str | None, status: str | None, task: str | None, limit: int) -> None:
    async def do_list() -> None:
        await init_db()
        async with async_session_factory() as session:
            repo = JobRepository(session)
            job_status = JobStatus(status) if status else None
            items, total = await repo.list_jobs(
                queue=queue,
                status=job_status,
                task_name=task,
                limit=limit,
            )

            table = Table(title=f"TaskForge Jobs ({len(items)}/{total})")
            table.add_column("ID", style="dim")
            table.add_column("Task", style="cyan")
            table.add_column("Queue", style="yellow")
            table.add_column("Status")
            table.add_column("Progress")
            table.add_column("Retries")
            table.add_column("Created At")

            for item in items:
                table.add_row(
                    item.id[:8] + "...",
                    item.task_name,
                    item.queue,
                    item.status,
                    f"{item.progress:.0f}%",
                    f"{item.retry_count}/{item.max_retries}",
                    item.created_at.strftime("%H:%M:%S"),
                )

            console.print(table)

    asyncio.run(do_list())


@main.command("cancel")
@click.argument("job_id")
def cancel_cmd(job_id: str) -> None:
    async def do_cancel() -> None:
        await init_db()
        async with async_session_factory() as session:
            repo = JobRepository(session)
            try:
                job = await repo.cancel_job(job_id)
                console.print(f"[green]Job {job.id} cancelled.[/green]")
            except Exception as err:
                console.print(f"[red]Failed to cancel job: {err}[/red]")

    asyncio.run(do_cancel())


@main.command("retry")
@click.argument("job_id")
def retry_cmd(job_id: str) -> None:
    async def do_retry() -> None:
        await init_db()
        async with async_session_factory() as session:
            repo = JobRepository(session)
            try:
                job = await repo.retry_job(job_id)
                console.print(f"[green]Job {job.id} reset to pending.[/green]")
            except Exception as err:
                console.print(f"[red]Failed to retry job: {err}[/red]")

    asyncio.run(do_retry())


@main.command("stats")
def stats_cmd() -> None:
    async def show_stats() -> None:
        await init_db()
        async with async_session_factory() as session:
            repo = JobRepository(session)
            stats = await repo.get_queue_stats()
            workers = await repo.list_workers()

            queue_table = Table(title="Queue Metrics")
            queue_table.add_column("Queue", style="bold yellow")
            queue_table.add_column("Pending", style="yellow")
            queue_table.add_column("Scheduled", style="blue")
            queue_table.add_column("Running", style="cyan")
            queue_table.add_column("Completed", style="green")
            queue_table.add_column("Failed", style="red")
            queue_table.add_column("Dead Letter", style="bold red")
            queue_table.add_column("Total", style="bold")

            for s in stats:
                queue_table.add_row(
                    s.queue,
                    str(s.pending),
                    str(s.scheduled),
                    str(s.running),
                    str(s.completed),
                    str(s.failed),
                    str(s.dead_letter),
                    str(s.total),
                )

            worker_table = Table(title="Active Workers")
            worker_table.add_column("Worker ID", style="cyan")
            worker_table.add_column("Host", style="dim")
            worker_table.add_column("PID")
            worker_table.add_column("Queues")
            worker_table.add_column("Concurrency")
            worker_table.add_column("Completed", style="green")
            worker_table.add_column("Failed", style="red")

            for w in workers:
                worker_table.add_row(
                    w.id,
                    w.hostname,
                    str(w.pid),
                    w.queues,
                    str(w.concurrency),
                    str(w.jobs_completed),
                    str(w.jobs_failed),
                )

            console.print(queue_table)
            console.print(worker_table)

    asyncio.run(show_stats())


@main.command("tasks")
def tasks_cmd() -> None:
    tasks = registry.list_tasks()
    table = Table(title="Registered Task Handlers")
    table.add_column("Task Name", style="bold cyan")
    table.add_column("Async", style="green")
    table.add_column("Timeout (s)", style="yellow")
    table.add_column("Max Retries", style="magenta")
    table.add_column("Default Queue", style="blue")

    for t in tasks:
        defn = registry.get(t)
        table.add_row(
            defn.name,
            str(defn.is_async),
            str(defn.timeout_seconds),
            str(defn.default_max_retries),
            defn.default_queue,
        )

    console.print(table)
