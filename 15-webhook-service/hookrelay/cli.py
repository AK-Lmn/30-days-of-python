import asyncio
import json
import click
import uvicorn
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.json import JSON
from hookrelay.config import settings
from hookrelay.database import async_session_factory, init_db
from hookrelay.schemas.endpoint import EndpointCreate
from hookrelay.schemas.subscription import SubscriptionCreate
from hookrelay.security.signer import generate_delivery_signature
from hookrelay.security.verifier import verify_hmac_sha256
from hookrelay.services.endpoint_service import EndpointService
from hookrelay.services.subscription_service import SubscriptionService
from hookrelay.services.event_service import EventService
from hookrelay.services.delivery_service import DeliveryService

console = Console()


@click.group()
def main() -> None:
    pass


@main.command()
@click.option("--host", default="127.0.0.1", help="Host address to bind")
@click.option("--port", default=8000, type=int, help="Port to listen on")
@click.option("--reload", is_flag=True, help="Enable autoreload")
def serve(host: str, port: int, reload: bool) -> None:
    console.print(f"[bold green]Starting HookRelay service on http://{host}:{port}[/bold green]")
    uvicorn.run("hookrelay.api.app:app", host=host, port=port, reload=reload)


@main.group()
def endpoint() -> None:
    pass


@endpoint.command("create")
@click.argument("slug")
@click.argument("name")
@click.option("--strategy", default="none", type=click.Choice(["none", "token", "hmac_sha256", "github", "stripe"]))
@click.option("--secret", default="", help="Secret key for verification")
@click.option("--description", default="", help="Description")
def create_endpoint_cmd(slug: str, name: str, strategy: str, secret: str, description: str) -> None:
    async def _run() -> None:
        await init_db()
        async with async_session_factory() as session:
            ep = await EndpointService.create(
                session,
                EndpointCreate(
                    slug=slug,
                    name=name,
                    verification_strategy=strategy,
                    secret=secret,
                    description=description,
                ),
            )
            await session.commit()
            console.print(f"[green]Endpoint created:[/green] [bold]{ep.id}[/bold] (slug: {ep.slug})")

    asyncio.run(_run())


@endpoint.command("list")
def list_endpoints_cmd() -> None:
    async def _run() -> None:
        await init_db()
        async with async_session_factory() as session:
            endpoints = await EndpointService.list_all(session)
            table = Table(title="Webhook Endpoints")
            table.add_column("ID", style="cyan")
            table.add_column("Slug", style="bold green")
            table.add_column("Name")
            table.add_column("Strategy", style="magenta")
            table.add_column("Active", justify="center")
            table.add_column("Created At")

            for ep in endpoints:
                table.add_row(
                    ep.id,
                    ep.slug,
                    ep.name,
                    ep.verification_strategy,
                    "[green]yes[/green]" if ep.is_active else "[red]no[/red]",
                    ep.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                )
            console.print(table)

    asyncio.run(_run())


@main.group()
def subscription() -> None:
    pass


@subscription.command("create")
@click.argument("name")
@click.argument("url")
@click.option("--pattern", multiple=True, default=["*"], help="Event patterns (e.g. payment.*)")
@click.option("--secret", default=None, help="Secret for signing deliveries")
@click.option("--retries", default=3, type=int, help="Max retries")
def create_sub_cmd(name: str, url: str, pattern: list[str], secret: str | None, retries: int) -> None:
    async def _run() -> None:
        await init_db()
        async with async_session_factory() as session:
            sub = await SubscriptionService.create(
                session,
                SubscriptionCreate(
                    name=name,
                    target_url=url,
                    event_patterns=list(pattern),
                    secret_token=secret,
                    max_retries=retries,
                ),
            )
            await session.commit()
            console.print(f"[green]Subscription created:[/green] [bold]{sub.id}[/bold] -> {sub.target_url}")

    asyncio.run(_run())


@subscription.command("list")
def list_subs_cmd() -> None:
    async def _run() -> None:
        await init_db()
        async with async_session_factory() as session:
            subs = await SubscriptionService.list_all(session)
            table = Table(title="Webhook Subscriptions")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="bold")
            table.add_column("Target URL", style="blue")
            table.add_column("Patterns", style="yellow")
            table.add_column("Retries", justify="right")
            table.add_column("Active", justify="center")

            for sub in subs:
                table.add_row(
                    sub.id,
                    sub.name,
                    sub.target_url,
                    ", ".join(sub.event_patterns),
                    str(sub.max_retries),
                    "[green]yes[/green]" if sub.is_active else "[red]no[/red]",
                )
            console.print(table)

    asyncio.run(_run())


@main.group()
def event() -> None:
    pass


@event.command("list")
@click.option("--limit", default=20, type=int)
def list_events_cmd(limit: int) -> None:
    async def _run() -> None:
        await init_db()
        async with async_session_factory() as session:
            events = await EventService.list_all(session, limit=limit)
            table = Table(title="Received Events")
            table.add_column("ID", style="cyan")
            table.add_column("Endpoint", style="green")
            table.add_column("Type", style="bold yellow")
            table.add_column("Idempotency Key")
            table.add_column("Status")
            table.add_column("Created At")

            for evt in events:
                status_color = "green" if evt.status == "processed" else "yellow"
                table.add_row(
                    evt.id,
                    evt.endpoint_id,
                    evt.event_type,
                    evt.idempotency_key or "-",
                    f"[{status_color}]{evt.status}[/{status_color}]",
                    evt.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                )
            console.print(table)

    asyncio.run(_run())


@event.command("show")
@click.argument("event_id")
def show_event_cmd(event_id: str) -> None:
    async def _run() -> None:
        await init_db()
        async with async_session_factory() as session:
            evt = await EventService.get_by_id(session, event_id)
            if not evt:
                console.print(f"[red]Event {event_id} not found[/red]")
                return

            console.print(Panel(
                f"[bold]ID:[/bold] {evt.id}\n"
                f"[bold]Endpoint:[/bold] {evt.endpoint_id}\n"
                f"[bold]Event Type:[/bold] {evt.event_type}\n"
                f"[bold]Idempotency Key:[/bold] {evt.idempotency_key}\n"
                f"[bold]Status:[/bold] {evt.status}\n"
                f"[bold]Created:[/bold] {evt.created_at}",
                title="Event Metadata",
            ))
            console.print(Panel(JSON(json.dumps(evt.payload)), title="Payload"))

    asyncio.run(_run())


@main.group()
def delivery() -> None:
    pass


@delivery.command("list")
@click.option("--status", default=None)
@click.option("--limit", default=20, type=int)
def list_deliveries_cmd(status: str | None, limit: int) -> None:
    async def _run() -> None:
        await init_db()
        async with async_session_factory() as session:
            deliveries = await DeliveryService.list_all(session, status=status, limit=limit)
            table = Table(title="Webhook Deliveries")
            table.add_column("ID", style="cyan")
            table.add_column("Event ID", style="dim")
            table.add_column("Subscription", style="green")
            table.add_column("Status", style="bold")
            table.add_column("Attempts", justify="right")
            table.add_column("Next Retry")

            for d in deliveries:
                status_color = "green" if d.status == "success" else ("red" if d.status in ("failed", "dlq") else "yellow")
                next_retry = d.next_retry_at.strftime("%H:%M:%S") if d.next_retry_at else "-"
                table.add_row(
                    d.id,
                    d.event_id,
                    d.subscription_id,
                    f"[{status_color}]{d.status}[/{status_color}]",
                    f"{d.attempts_count}/{d.max_retries}",
                    next_retry,
                )
            console.print(table)

    asyncio.run(_run())


@delivery.command("replay")
@click.argument("delivery_id")
def replay_cmd(delivery_id: str) -> None:
    async def _run() -> None:
        await init_db()
        async with async_session_factory() as session:
            try:
                delivery, attempt = await DeliveryService.replay_delivery(session, delivery_id)
                await session.commit()
                status_color = "green" if delivery.status == "success" else "red"
                console.print(
                    f"Replay complete: [{status_color}]{delivery.status}[/{status_color}] "
                    f"(HTTP {attempt.status_code if attempt else '-'}, duration {attempt.duration_ms if attempt else 0}ms)"
                )
            except Exception as exc:
                console.print(f"[red]Error replaying delivery:[/red] {exc}")

    asyncio.run(_run())


@delivery.command("process-retries")
def process_retries_cmd() -> None:
    async def _run() -> None:
        await init_db()
        async with async_session_factory() as session:
            processed = await DeliveryService.process_pending_retries(session)
            await session.commit()
            console.print(f"[green]Processed {len(processed)} pending retries[/green]")

    asyncio.run(_run())


@main.command()
@click.argument("slug")
@click.option("--type", "event_type", default="order.created")
@click.option("--payload", default='{"order_id": 1234, "total": 99.99}')
@click.option("--idempotency-key", default=None)
def simulate(slug: str, event_type: str, payload: str, idempotency_key: str | None) -> None:
    async def _run() -> None:
        await init_db()
        async with async_session_factory() as session:
            ep = await EndpointService.get_by_slug(session, slug)
            if not ep:
                console.print(f"[red]Endpoint with slug '{slug}' not found[/red]")
                return

            raw_bytes = payload.encode("utf-8")
            headers = {"content-type": "application/json", "x-event-type": event_type}
            if idempotency_key:
                headers["idempotency-key"] = idempotency_key

            if ep.verification_strategy == "github":
                sig, _ = generate_delivery_signature(raw_bytes, ep.secret)
                v1_sig = sig.split("v1=")[-1]
                headers["x-hub-signature-256"] = f"sha256={v1_sig}"
            elif ep.verification_strategy == "stripe":
                sig, _ = generate_delivery_signature(raw_bytes, ep.secret)
                headers["stripe-signature"] = sig
            elif ep.verification_strategy == "token":
                headers["x-webhook-token"] = ep.secret

            event, count, is_dup = await EventService.ingest_event(
                session, ep, raw_bytes, headers
            )
            await session.commit()

            if is_dup:
                console.print(f"[yellow]Duplicate event detected: {event.id}[/yellow]")
            else:
                console.print(
                    f"[green]Simulated event ingested successfully:[/green] {event.id} "
                    f"([bold]{event.event_type}[/bold]), scheduled {count} deliveries."
                )

    asyncio.run(_run())
