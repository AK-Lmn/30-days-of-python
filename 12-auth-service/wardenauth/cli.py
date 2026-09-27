import asyncio
import json
import click
import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from wardenauth import __version__
from wardenauth.config import get_settings
from wardenauth.core.hashing import hash_password
from wardenauth.core.permissions import Role, get_scopes_for_role
from wardenauth.core.tokens import create_access_token, decode_jwt
from wardenauth.database import AsyncSessionLocal, init_db
from wardenauth.models.entities import Session as SessionEntity, User
from wardenauth.models.schemas import UserRegisterRequest
from wardenauth.repositories.user_repo import UserRepo
from wardenauth.services.audit_service import AuditService
from wardenauth.services.session_service import SessionService
from wardenauth.services.user_service import UserService

console = Console()


@click.group()
@click.version_option(version=__version__)
def cli() -> None:
    pass


@cli.command()
@click.option("--host", default="127.0.0.1", help="Host address to bind.")
@click.option("--port", default=8000, type=int, help="Port to bind.")
@click.option("--reload", is_flag=True, help="Enable auto-reload on code change.")
def serve(host: str, port: int, reload: bool) -> None:
    console.print(
        Panel(
            f"[bold green]Starting WardenAuth Service[/bold green]\n"
            f"Host: [cyan]{host}:{port}[/cyan]\n"
            f"Docs: [cyan]http://{host}:{port}/docs[/cyan]",
            title="WardenAuth Daemon",
            border_style="green",
        )
    )
    uvicorn.run("wardenauth.main:app", host=host, port=port, reload=reload)


@cli.command()
@click.option("--email", prompt=True, help="User email address.")
@click.option("--username", prompt=True, help="Username.")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True, help="Password.")
@click.option("--full-name", default=None, help="User full name.")
@click.option(
    "--role",
    type=click.Choice(["admin", "manager", "user"], case_sensitive=False),
    default="user",
    help="User role.",
)
def create_user(
    email: str,
    username: str,
    password: str,
    full_name: str | None,
    role: str,
) -> None:
    async def _runner():
        await init_db()
        UserRegisterRequest(
            email=email,
            username=username,
            password=password,
            full_name=full_name,
        )

        async with AsyncSessionLocal() as session:
            user_repo = UserRepo(session)
            if await user_repo.get_by_email(email):
                console.print(f"[bold red]Error:[/bold red] Email '{email}' is already registered.")
                return
            if await user_repo.get_by_username(username):
                console.print(f"[bold red]Error:[/bold red] Username '{username}' is already taken.")
                return

            pw_hash = hash_password(password)
            user = await user_repo.create(
                email=email,
                username=username,
                password_hash=pw_hash,
                full_name=full_name,
                role=role.lower(),
                status="active",
            )
            audit_service = AuditService(session)
            await audit_service.log_event(
                event_type="cli.user.created",
                user_id=user.id,
                details={"username": user.username, "role": user.role},
            )
            console.print(
                Panel(
                    f"[bold green]User created successfully![/bold green]\n\n"
                    f"ID: [cyan]{user.id}[/cyan]\n"
                    f"Username: [cyan]{user.username}[/cyan]\n"
                    f"Email: [cyan]{user.email}[/cyan]\n"
                    f"Role: [yellow]{user.role}[/yellow]\n"
                    f"Status: [green]{user.status}[/green]",
                    title="User Provisioning",
                    border_style="green",
                )
            )

    try:
        asyncio.run(_runner())
    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")


@cli.command()
@click.option("--limit", default=20, type=int, help="Limit number of users.")
@click.option("--search", default=None, help="Search query.")
def list_users(limit: int, search: str | None) -> None:
    async def _runner():
        await init_db()
        async with AsyncSessionLocal() as session:
            user_service = UserService(session)
            users, total = await user_service.list_users(offset=0, limit=limit, search=search)

            table = Table(title=f"Registered Users (Showing {len(users)} of {total})")
            table.add_column("ID", style="dim")
            table.add_column("Username", style="cyan bold")
            table.add_column("Email", style="blue")
            table.add_column("Role", style="yellow")
            table.add_column("Status", style="green")
            table.add_column("Created At", style="dim")

            for user in users:
                status_style = "green" if user.status == "active" else "red"
                table.add_row(
                    user.id[:8],
                    user.username,
                    user.email,
                    user.role,
                    f"[{status_style}]{user.status}[/{status_style}]",
                    user.created_at.strftime("%Y-%m-%d %H:%M"),
                )
            console.print(table)

    asyncio.run(_runner())


@cli.command()
@click.argument("username_or_email")
def issue_token(username_or_email: str) -> None:
    async def _runner():
        await init_db()
        async with AsyncSessionLocal() as session:
            user_repo = UserRepo(session)
            user = await user_repo.get_by_username_or_email(username_or_email)
            if not user:
                console.print(f"[bold red]User not found:[/bold red] {username_or_email}")
                return

            scopes = get_scopes_for_role(user.role)
            dummy_session_id = "cli-token-session"
            token = create_access_token(
                user_id=user.id,
                role=user.role,
                scopes=scopes,
                session_id=dummy_session_id,
            )
            console.print(
                Panel(
                    f"[bold green]Issued Access Token for {user.username} ({user.role}):[/bold green]\n\n"
                    f"[cyan]{token}[/cyan]",
                    title="Token Issuer",
                    border_style="cyan",
                )
            )

    asyncio.run(_runner())


@cli.command()
@click.argument("jwt_token")
def inspect_token(jwt_token: str) -> None:
    try:
        payload = decode_jwt(jwt_token)
        console.print(
            Panel(
                json.dumps(payload, indent=2),
                title="Decoded Token Payload",
                border_style="green",
            )
        )
    except Exception as exc:
        console.print(f"[bold red]Failed to decode token:[/bold red] {exc}")


@cli.command()
@click.option("--limit", default=20, type=int, help="Number of audit logs to display.")
def audit_logs(limit: int) -> None:
    async def _runner():
        await init_db()
        async with AsyncSessionLocal() as session:
            audit_service = AuditService(session)
            logs, total = await audit_service.list_logs(offset=0, limit=limit)

            table = Table(title=f"Audit Logs (Showing {len(logs)} of {total})")
            table.add_column("Timestamp", style="dim", no_wrap=True)
            table.add_column("Event Type", style="cyan bold")
            table.add_column("User ID", style="magenta")
            table.add_column("IP Address", style="yellow")
            table.add_column("Details", style="white")

            for log in logs:
                table.add_row(
                    log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    log.event_type,
                    log.user_id[:8] if log.user_id else "system",
                    log.ip_address or "-",
                    log.details or "-",
                )
            console.print(table)

    asyncio.run(_runner())


@cli.command()
def stats() -> None:
    async def _runner():
        await init_db()
        async with AsyncSessionLocal() as session:
            user_service = UserService(session)
            session_service = SessionService(session)
            audit_service = AuditService(session)

            user_stats = await user_service.get_user_stats()
            active_sessions = await session_service.count_active()
            recent_events = await audit_service.count_recent(60)

            table = Table(title="WardenAuth System Telemetry")
            table.add_column("Metric", style="cyan bold")
            table.add_column("Value", style="green")

            table.add_row("Total Users", str(user_stats["total_users"]))
            table.add_row("Active Users", str(user_stats["active_users"]))
            table.add_row("Suspended Users", str(user_stats["suspended_users"]))
            table.add_row("Active Sessions", str(active_sessions))
            table.add_row("Events (Last 60m)", str(recent_events))

            console.print(table)

    asyncio.run(_runner())


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
