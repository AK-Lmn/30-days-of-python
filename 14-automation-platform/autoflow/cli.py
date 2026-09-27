import asyncio
import json
from pathlib import Path
from typing import Any, Optional
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import uvicorn

from autoflow.database import async_session_factory, init_db
from autoflow.engine.executor import WorkflowExecutor
from autoflow.engine.registry import registry
from autoflow.models.enums import ActionType, ComparisonOperator, TriggerType
from autoflow.models.schemas import ConditionSchema, EventIngestRequest, StepCreate, WorkflowCreate
from autoflow.repositories.run_repo import RunRepository
from autoflow.repositories.workflow_repo import WorkflowRepository

console = Console()


def run_async(coro: Any) -> Any:
    return asyncio.run(coro)


@click.group()
def main() -> None:
    pass


@main.command()
@click.option("--host", default="127.0.0.1")
@click.option("--port", default=8000)
@click.option("--reload", is_flag=True, default=False)
def server(host: str, port: int, reload: bool) -> None:
    console.print(Panel(f"[bold cyan]AutoFlow Platform[/bold cyan] starting on [green]http://{host}:{port}[/green]"))
    uvicorn.run(
        "autoflow.main:app",
        host=host,
        port=port,
        reload=reload,
    )


@main.group()
def workflow() -> None:
    pass


@workflow.command("list")
def list_workflows_cmd() -> None:
    async def _run() -> None:
        await init_db()
        async with async_session_factory() as session:
            repo = WorkflowRepository(session)
            workflows = await repo.list_with_counts()

            if not workflows:
                console.print("[yellow]No workflows found. Use 'autoflow init-sample' or 'autoflow workflow create'[/yellow]")
                return

            table = Table(title="Configured Automations")
            table.add_column("ID", style="dim", width=36)
            table.add_column("Name", style="bold green")
            table.add_column("Trigger", style="cyan")
            table.add_column("Enabled", style="magenta")
            table.add_column("Steps", justify="right")
            table.add_column("Runs", justify="right")

            for wf in workflows:
                status_str = "[green]Yes[/green]" if wf["enabled"] else "[red]No[/red]"
                table.add_row(
                    wf["id"],
                    wf["name"],
                    wf["trigger_type"],
                    status_str,
                    str(wf["steps_count"]),
                    str(wf["runs_count"]),
                )
            console.print(table)

    run_async(_run())


@workflow.command("get")
@click.argument("workflow_id")
def get_workflow_cmd(workflow_id: str) -> None:
    async def _run() -> None:
        await init_db()
        async with async_session_factory() as session:
            repo = WorkflowRepository(session)
            wf = await repo.get_by_id(workflow_id)
            if not wf:
                console.print(f"[red]Workflow '{workflow_id}' not found[/red]")
                return

            console.print(Panel(
                f"[bold cyan]{wf.name}[/bold cyan] ({wf.id})\n"
                f"[dim]{wf.description or 'No description'}[/dim]\n\n"
                f"[bold]Trigger:[/bold] {wf.trigger_type} {json.dumps(wf.trigger_config)}\n"
                f"[bold]Enabled:[/bold] {wf.enabled}\n"
                f"[bold]Conditions:[/bold] {json.dumps(wf.conditions)}\n"
                f"[bold]Steps ({len(wf.steps)}):[/bold]"
            ))

            if wf.steps:
                table = Table()
                table.add_column("Order", justify="right", width=6)
                table.add_column("Step Name", style="bold")
                table.add_column("Action Type", style="cyan")
                table.add_column("Config", style="dim")
                for s in wf.steps:
                    table.add_row(str(s.step_order), s.step_name, s.action_type, json.dumps(s.action_config))
                console.print(table)

    run_async(_run())


@workflow.command("create")
@click.option("-f", "--file", "file_path", required=True, type=click.Path(exists=True))
def create_workflow_cmd(file_path: str) -> None:
    async def _run() -> None:
        await init_db()
        raw_text = Path(file_path).read_text(encoding="utf-8")
        data = json.loads(raw_text)
        payload = WorkflowCreate.model_validate(data)

        async with async_session_factory() as session:
            repo = WorkflowRepository(session)
            wf = await repo.create(payload)
            await session.commit()
            console.print(f"[green]Workflow '{wf.name}' created with ID: [bold]{wf.id}[/bold][/green]")

    run_async(_run())


@workflow.command("toggle")
@click.argument("workflow_id")
def toggle_workflow_cmd(workflow_id: str) -> None:
    async def _run() -> None:
        await init_db()
        async with async_session_factory() as session:
            repo = WorkflowRepository(session)
            wf = await repo.toggle(workflow_id)
            if not wf:
                console.print(f"[red]Workflow '{workflow_id}' not found[/red]")
                return
            await session.commit()
            state = "[green]enabled[/green]" if wf.enabled else "[red]disabled[/red]"
            console.print(f"Workflow '{wf.name}' is now {state}")

    run_async(_run())


@workflow.command("delete")
@click.argument("workflow_id")
def delete_workflow_cmd(workflow_id: str) -> None:
    async def _run() -> None:
        await init_db()
        async with async_session_factory() as session:
            repo = WorkflowRepository(session)
            deleted = await repo.delete(workflow_id)
            if deleted:
                await session.commit()
                console.print(f"[green]Workflow '{workflow_id}' deleted successfully[/green]")
            else:
                console.print(f"[red]Workflow '{workflow_id}' not found[/red]")

    run_async(_run())


@workflow.command("run")
@click.argument("workflow_id")
@click.option("--payload", "-p", default="{}")
def run_workflow_cmd(workflow_id: str, payload: str) -> None:
    async def _run() -> None:
        await init_db()
        payload_data = json.loads(payload)
        async with async_session_factory() as session:
            repo = WorkflowRepository(session)
            wf = await repo.get_by_id(workflow_id)
            if not wf:
                console.print(f"[red]Workflow '{workflow_id}' not found[/red]")
                return

            executor = WorkflowExecutor(session)
            run = await executor.execute_workflow(
                workflow=wf,
                trigger_type=TriggerType.MANUAL.value,
                trigger_payload=payload_data,
            )

            color = "green" if run.status == "completed" else "yellow" if run.status == "skipped" else "red"
            console.print(Panel(
                f"[bold]Run ID:[/bold] {run.id}\n"
                f"[bold]Status:[/bold] [{color}]{run.status.upper()}[/{color}]\n"
                f"[bold]Duration:[/bold] {run.duration_ms:.2f}ms\n"
                f"[bold]Error:[/bold] {run.error_message or 'None'}"
            ))

            if run.step_runs:
                table = Table(title="Step Execution Details")
                table.add_column("Step", style="bold")
                table.add_column("Action", style="cyan")
                table.add_column("Status")
                table.add_column("Duration")
                table.add_column("Output / Error", style="dim")

                for sr in run.step_runs:
                    st_color = "green" if sr.status == "success" else "red"
                    out_str = json.dumps(sr.output_data) if sr.status == "success" else sr.error_message
                    table.add_row(
                        sr.step_name,
                        sr.action_type,
                        f"[{st_color}]{sr.status}[/{st_color}]",
                        f"{sr.duration_ms:.2f}ms" if sr.duration_ms else "-",
                        str(out_str),
                    )
                console.print(table)

    run_async(_run())


@main.group()
def event() -> None:
    pass


@event.command("emit")
@click.argument("event_name")
@click.option("--payload", "-p", default="{}")
def emit_event_cmd(event_name: str, payload: str) -> None:
    async def _run() -> None:
        await init_db()
        payload_data = json.loads(payload)

        async with async_session_factory() as session:
            wf_repo = WorkflowRepository(session)
            run_repo = RunRepository(session)

            matched_workflows = await wf_repo.get_active_event_workflows(event_name)
            event_log = await run_repo.record_event(
                event_name=event_name,
                payload=payload_data,
                matched_count=len(matched_workflows),
            )

            console.print(f"[bold cyan]Emitted Event:[/bold cyan] {event_name} (Logged ID: {event_log.id})")
            console.print(f"[bold]Matched Workflows:[/bold] {len(matched_workflows)}")

            executor = WorkflowExecutor(session)
            for wf in matched_workflows:
                run = await executor.execute_workflow(
                    workflow=wf,
                    trigger_type=TriggerType.EVENT.value,
                    trigger_payload=payload_data,
                )
                col = "green" if run.status == "completed" else "yellow" if run.status == "skipped" else "red"
                console.print(f" -> Workflow '{wf.name}' executed: [{col}]{run.status}[/{col}] (Run: {run.id})")

    run_async(_run())


@event.command("list")
@click.option("--limit", default=20)
def list_events_cmd(limit: int) -> None:
    async def _run() -> None:
        await init_db()
        async with async_session_factory() as session:
            repo = RunRepository(session)
            events = await repo.list_events(limit=limit)

            table = Table(title="Recent Ingested Events")
            table.add_column("Event ID", style="dim", width=36)
            table.add_column("Event Name", style="bold green")
            table.add_column("Matched", justify="right")
            table.add_column("Received At", style="cyan")

            for e in events:
                table.add_row(e.id, e.event_name, str(e.matched_workflows_count), e.received_at.strftime("%Y-%m-%d %H:%M:%S"))
            console.print(table)

    run_async(_run())


@main.group()
def run() -> None:
    pass


@run.command("list")
@click.option("--workflow-id", default=None)
@click.option("--status", default=None)
@click.option("--limit", default=20)
def list_runs_cmd(workflow_id: Optional[str], status: Optional[str], limit: int) -> None:
    async def _run() -> None:
        await init_db()
        async with async_session_factory() as session:
            repo = RunRepository(session)
            runs = await repo.list_runs(workflow_id=workflow_id, status=status, limit=limit)

            table = Table(title="Workflow Execution History")
            table.add_column("Run ID", style="dim", width=36)
            table.add_column("Workflow ID", style="dim", width=36)
            table.add_column("Trigger", style="cyan")
            table.add_column("Status")
            table.add_column("Duration")
            table.add_column("Started At")

            for r in runs:
                col = "green" if r.status == "completed" else "yellow" if r.status == "skipped" else "red"
                dur = f"{r.duration_ms:.2f}ms" if r.duration_ms is not None else "-"
                table.add_row(
                    r.id,
                    r.workflow_id,
                    r.trigger_type,
                    f"[{col}]{r.status}[/{col}]",
                    dur,
                    r.started_at.strftime("%Y-%m-%d %H:%M:%S") if r.started_at else "-",
                )
            console.print(table)

    run_async(_run())


@run.command("get")
@click.argument("run_id")
def get_run_cmd(run_id: str) -> None:
    async def _run() -> None:
        await init_db()
        async with async_session_factory() as session:
            repo = RunRepository(session)
            r = await repo.get_run_by_id(run_id)
            if not r:
                console.print(f"[red]Run '{run_id}' not found[/red]")
                return

            color = "green" if r.status == "completed" else "yellow" if r.status == "skipped" else "red"
            console.print(Panel(
                f"[bold cyan]Run Details[/bold cyan]\n"
                f"[bold]ID:[/bold] {r.id}\n"
                f"[bold]Workflow ID:[/bold] {r.workflow_id}\n"
                f"[bold]Trigger Type:[/bold] {r.trigger_type}\n"
                f"[bold]Status:[/bold] [{color}]{r.status.upper()}[/{color}]\n"
                f"[bold]Duration:[/bold] {r.duration_ms:.2f}ms\n"
                f"[bold]Payload:[/bold] {json.dumps(r.trigger_payload)}\n"
                f"[bold]Error:[/bold] {r.error_message or 'None'}"
            ))

            if r.step_runs:
                table = Table(title="Step Runs")
                table.add_column("Step Name", style="bold")
                table.add_column("Action", style="cyan")
                table.add_column("Status")
                table.add_column("Duration")
                table.add_column("Output")

                for sr in r.step_runs:
                    st_color = "green" if sr.status == "success" else "red"
                    table.add_row(
                        sr.step_name,
                        sr.action_type,
                        f"[{st_color}]{sr.status}[/{st_color}]",
                        f"{sr.duration_ms:.2f}ms" if sr.duration_ms else "-",
                        json.dumps(sr.output_data),
                    )
                console.print(table)

    run_async(_run())


@main.command()
def actions() -> None:
    table = Table(title="Available Action Types")
    table.add_column("Type", style="bold green")
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    table.add_column("Parameters", style="dim")

    for act in registry.list_actions():
        table.add_row(
            act.action_type,
            act.display_name,
            act.description,
            ", ".join(act.parameters_schema.keys()),
        )
    console.print(table)


@main.command()
def stats() -> None:
    async def _run() -> None:
        await init_db()
        async with async_session_factory() as session:
            repo = RunRepository(session)
            st = await repo.get_stats()

            table = Table(title="Platform Statistics")
            table.add_column("Metric", style="bold cyan")
            table.add_column("Value", justify="right", style="green")

            for k, v in st.items():
                table.add_row(k.replace("_", " ").title(), str(v))
            console.print(table)

    run_async(_run())


@main.command("init-sample")
def init_sample() -> None:
    async def _run() -> None:
        await init_db()
        async with async_session_factory() as session:
            repo = WorkflowRepository(session)

            sample_event_wf = WorkflowCreate(
                name="Order Notification & Enrichment",
                description="Triggered when an order is created, formats details and notifies customer",
                enabled=True,
                trigger_type=TriggerType.EVENT,
                trigger_config={"event_name": "order.created"},
                conditions=[
                    ConditionSchema(
                        field="event.amount",
                        operator=ComparisonOperator.GREATER_THAN,
                        value=50,
                    )
                ],
                steps=[
                    StepCreate(
                        step_order=0,
                        step_name="enrich_order",
                        action_type=ActionType.TRANSFORM.value,
                        action_config={
                            "mapping": {
                                "customer_name": "{{ event.customer_name }}",
                                "order_id": "{{ event.order_id }}",
                                "tier": "VIP Order",
                            }
                        },
                    ),
                    StepCreate(
                        step_order=1,
                        step_name="notify_customer",
                        action_type=ActionType.NOTIFICATION.value,
                        action_config={
                            "channel": "email",
                            "recipient": "{{ event.email }}",
                            "subject": "Order Confirmation: {{ event.order_id }}",
                            "message": "Hello {{ steps.enrich_order.result.customer_name }}, your order of ${{ event.amount }} has been received!",
                        },
                    ),
                    StepCreate(
                        step_order=2,
                        step_name="log_to_file",
                        action_type=ActionType.FILE_APPEND.value,
                        action_config={
                            "path": "automation_orders.log",
                            "content": "Order: {{ event.order_id }} processed for {{ event.customer_name }}",
                        },
                    ),
                ],
            )

            sample_scheduled_wf = WorkflowCreate(
                name="Periodic Health Beat",
                description="Runs every 30 seconds to log heartbeat",
                enabled=True,
                trigger_type=TriggerType.SCHEDULE,
                trigger_config={"interval_seconds": 30},
                conditions=[],
                steps=[
                    StepCreate(
                        step_order=0,
                        step_name="record_heartbeat",
                        action_type=ActionType.NOTIFICATION.value,
                        action_config={
                            "channel": "console",
                            "recipient": "ops-team@example.com",
                            "message": "Heartbeat at {{ trigger.workflow_name }}",
                        },
                    )
                ],
            )

            wf1 = await repo.create(sample_event_wf)
            wf2 = await repo.create(sample_scheduled_wf)
            await session.commit()

            console.print(f"[green]Sample event workflow created:[/green] [bold]{wf1.name}[/bold] ({wf1.id})")
            console.print(f"[green]Sample scheduled workflow created:[/green] [bold]{wf2.name}[/bold] ({wf2.id})")

    run_async(_run())


if __name__ == "__main__":
    main()
