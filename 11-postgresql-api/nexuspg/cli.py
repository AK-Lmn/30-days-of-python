import asyncio
import json
import sys
import click
from rich.console import Console
from rich.table import Table
import uvicorn
from sqlalchemy import text
from nexuspg.core.config import settings
from nexuspg.db.session import async_session_maker, init_db
from nexuspg.repositories.flag_repo import FlagRepository
from nexuspg.repositories.project_repo import ProjectRepository
from nexuspg.schemas.flag import (
    FlagCreate,
    FlagEnvironmentStateUpdate,
    RuleConditionCreate,
    TargetingRuleCreate,
)
from nexuspg.schemas.project import ProjectCreate

console = Console()


@click.group()
def main():
    pass


@main.command()
@click.option("--host", default="127.0.0.1", help="Host address to bind to")
@click.option("--port", default=8000, type=int, help="Port to listen on")
@click.option("--reload", is_flag=True, default=False, help="Enable auto-reload")
def serve(host: str, port: int, reload: bool):
    console.print(f"[bold green]Starting NexusPG API server on[/bold green] http://{host}:{port}")
    uvicorn.run("nexuspg.main:app", host=host, port=port, reload=reload)


@main.group()
def db():
    pass


@db.command("ping")
def db_ping():
    async def _ping():
        try:
            async with async_session_maker() as session:
                await session.execute(text("SELECT 1"))
            console.print("[bold green]Database connection successful![/bold green]")
        except Exception as exc:
            console.print(f"[bold red]Database connection failed: {exc}[/bold red]")
            sys.exit(1)

    asyncio.run(_ping())


@db.command("init")
def db_init():
    async def _init():
        await init_db()
        console.print("[bold green]Database tables created successfully![/bold green]")

    asyncio.run(_init())


@db.command("migrate")
@click.option("--revision", default="head", help="Alembic revision target")
def db_migrate(revision: str):
    from alembic import command
    from alembic.config import Config

    cfg = Config("alembic.ini")
    command.upgrade(cfg, revision)
    console.print(f"[bold green]Applied migration to '{revision}' successfully![/bold green]")


@db.command("rollback")
@click.option("--revision", default="-1", help="Alembic revision target to rollback to")
def db_rollback(revision: str):
    from alembic import command
    from alembic.config import Config

    cfg = Config("alembic.ini")
    command.downgrade(cfg, revision)
    console.print(f"[bold yellow]Rolled back migration to '{revision}' successfully![/bold yellow]")


@db.command("seed")
def db_seed():
    async def _seed():
        await init_db()
        async with async_session_maker() as session:
            project_repo = ProjectRepository(session)
            flag_repo = FlagRepository(session)

            p1 = await project_repo.get_by_key("ecommerce-platform")
            if not p1:
                p1 = await project_repo.create(
                    ProjectCreate(
                        key="ecommerce-platform",
                        name="E-Commerce Core Platform",
                        description="Global retail checkout and storefront platform",
                    )
                )

            p2 = await project_repo.get_by_key("mobile-app")
            if not p2:
                p2 = await project_repo.create(
                    ProjectCreate(
                        key="mobile-app",
                        name="Mobile Application",
                        description="iOS and Android customer application",
                    )
                )

            await session.commit()

            f1 = await flag_repo.get_by_key(p1.id, "enable-instant-checkout")
            if not f1:
                f1 = await flag_repo.create(
                    p1.id,
                    FlagCreate(
                        key="enable-instant-checkout",
                        name="Enable Instant Checkout Flow",
                        description="One-click checkout button with Apple Pay / Google Pay",
                        flag_type="boolean",
                        default_value=False,
                        tags=["checkout", "payments", "q3-release"],
                    ),
                )

            f2 = await flag_repo.get_by_key(p1.id, "cart-recommendation-model")
            if not f2:
                f2 = await flag_repo.create(
                    p1.id,
                    FlagCreate(
                        key="cart-recommendation-model",
                        name="Cart Recommendation Model",
                        description="ML model variant for cross-selling recommendations",
                        flag_type="string",
                        default_value="baseline-rules",
                        tags=["ml", "recommendations"],
                    ),
                )

            f3 = await flag_repo.get_by_key(p2.id, "new-nav-bar")
            if not f3:
                f3 = await flag_repo.create(
                    p2.id,
                    FlagCreate(
                        key="new-nav-bar",
                        name="Bottom Navigation Redesign",
                        description="Redesigned bottom tab bar with haptic feedback",
                        flag_type="boolean",
                        default_value=False,
                        tags=["mobile", "ui"],
                    ),
                )

            await session.commit()

            prod_env = await project_repo.get_environment_by_key(p1.id, "production")
            if prod_env and f1:
                await flag_repo.update_environment_state(
                    f1.id,
                    prod_env.id,
                    FlagEnvironmentStateUpdate(
                        enabled=True,
                        percentage=50,
                        variant_value=True,
                        rules=[
                            TargetingRuleCreate(
                                priority=0,
                                name="Internal Beta Testers",
                                serve_value=True,
                                percentage=100,
                                conditions=[
                                    RuleConditionCreate(
                                        attribute="email",
                                        operator="ends_with",
                                        values="@company.com",
                                    )
                                ],
                            ),
                            TargetingRuleCreate(
                                priority=1,
                                name="VIP Tier Customers",
                                serve_value=True,
                                percentage=100,
                                conditions=[
                                    RuleConditionCreate(
                                        attribute="tier",
                                        operator="in",
                                        values=["gold", "platinum"],
                                    )
                                ],
                            ),
                        ],
                    ),
                )

            dev_env = await project_repo.get_environment_by_key(p1.id, "development")
            if dev_env and f1:
                await flag_repo.update_environment_state(
                    f1.id,
                    dev_env.id,
                    FlagEnvironmentStateUpdate(
                        enabled=True,
                        percentage=100,
                        variant_value=True,
                    ),
                )

            await session.commit()

        console.print("[bold green]Seeded database successfully with demo projects, flags, rules, and tags![/bold green]")

    asyncio.run(_seed())


@main.group()
def projects():
    pass


@projects.command("list")
def list_projects_cmd():
    async def _list():
        async with async_session_maker() as session:
            repo = ProjectRepository(session)
            items, total = await repo.list(offset=0, limit=100)

            table = Table(title=f"Projects ({total} total)")
            table.add_column("Key", style="cyan")
            table.add_column("Name", style="bold")
            table.add_column("Environments", style="green")
            table.add_column("Created At", style="dim")

            for p in items:
                envs_str = ", ".join([e.key for e in p.environments])
                table.add_row(p.key, p.name, envs_str, str(p.created_at)[:19])

            console.print(table)

    asyncio.run(_list())


@main.group()
def flags():
    pass


@flags.command("list")
@click.option("--project", "project_key", required=True, help="Project key")
def list_flags_cmd(project_key: str):
    async def _list():
        async with async_session_maker() as session:
            project_repo = ProjectRepository(session)
            flag_repo = FlagRepository(session)

            project = await project_repo.get_by_key(project_key)
            if not project:
                console.print(f"[bold red]Project '{project_key}' not found[/bold red]")
                sys.exit(1)

            items, total = await flag_repo.list(project.id, offset=0, limit=100)

            table = Table(title=f"Flags in {project.name} ({total} total)")
            table.add_column("Key", style="cyan")
            table.add_column("Name", style="bold")
            table.add_column("Type", style="magenta")
            table.add_column("Default Value", style="yellow")
            table.add_column("Tags", style="blue")

            for f in items:
                tags_str = ", ".join([t.name for t in f.tags])
                table.add_row(f.key, f.name, f.flag_type, str(f.default_value), tags_str)

            console.print(table)

    asyncio.run(_list())


@main.command("evaluate")
@click.option("--project", "project_key", required=True, help="Project key")
@click.option("--env", "env_key", required=True, help="Environment key")
@click.option("--flag", "flag_key", required=True, help="Flag key")
@click.option("--user-id", default=None, help="Context user ID")
@click.option("--attr", multiple=True, help="Attribute key=value pair (can repeat)")
def evaluate_cmd(project_key: str, env_key: str, flag_key: str, user_id: str | None, attr: tuple[str, ...]):
    async def _eval():
        from nexuspg.routers.evaluation import evaluate_single_flag

        attributes = {}
        for item in attr:
            if "=" in item:
                k, v = item.split("=", 1)
                attributes[k] = v

        async with async_session_maker() as session:
            project_repo = ProjectRepository(session)
            flag_repo = FlagRepository(session)

            project = await project_repo.get_by_key(project_key)
            if not project:
                console.print(f"[bold red]Project '{project_key}' not found[/bold red]")
                sys.exit(1)

            env = await project_repo.get_environment_by_key(project.id, env_key)
            if not env:
                console.print(f"[bold red]Environment '{env_key}' not found[/bold red]")
                sys.exit(1)

            pairs = await flag_repo.list_for_evaluation(project.id, env.id, [flag_key])
            if not pairs:
                console.print(f"[bold red]Flag '{flag_key}' not found[/bold red]")
                sys.exit(1)

            flag, state = pairs[0]
            result = evaluate_single_flag(
                flag_key=flag.key,
                flag_type=flag.flag_type,
                default_val=flag.default_value,
                state_enabled=state.enabled,
                state_pct=state.percentage,
                state_variant_val=state.variant_value,
                rules=state.rules,
                user_id=user_id,
                attributes=attributes,
            )

            console.print(f"[bold]Flag:[/bold] {result.flag_key}")
            console.print(f"[bold]Enabled:[/bold] [{'green' if result.enabled else 'red'}]{result.enabled}[/]")
            console.print(f"[bold]Value:[/bold] {result.value}")
            console.print(f"[bold]Reason:[/bold] {result.reason}")
            if result.rule_id:
                console.print(f"[bold]Rule ID:[/bold] {result.rule_id}")

    asyncio.run(_eval())


if __name__ == "__main__":
    main()
