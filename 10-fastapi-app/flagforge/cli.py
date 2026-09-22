import asyncio
import json
import click
import uvicorn
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from flagforge.config import settings
from flagforge.core.evaluator import evaluate_flag
from flagforge.models.flag import FlagCreate, FlagType, TargetingRule, RuleCondition, Operator
from flagforge.models.evaluation import EvaluationContext
from flagforge.repositories.memory import InMemoryFlagRepository

console = Console()


@click.group()
def main():
    pass


@main.command()
@click.option("--host", default="0.0.0.0", help="Host interface to bind")
@click.option("--port", default=8000, type=int, help="Port to listen on")
@click.option("--reload", is_flag=True, default=False, help="Enable auto-reload")
def serve(host: str, port: int, reload: bool):
    console.print(Panel(f"[bold cyan]Starting FlagForge API[/bold cyan] at [green]http://{host}:{port}[/green]"))
    uvicorn.run("flagforge.main:app", host=host, port=port, reload=reload)


@main.command()
def seed():
    async def _seed():
        repo = InMemoryFlagRepository(settings.get_storage_path())
        seed_flags = [
            FlagCreate(
                key="dark-mode-v2",
                name="Dark Mode V2",
                description="Refreshed dark mode theme with AMOLED high contrast",
                flag_type=FlagType.BOOLEAN,
                enabled=True,
                default_value=False,
                tags=["ui", "theme", "frontend"],
                rules=[
                    TargetingRule(
                        name="Beta Testers",
                        conditions=[
                            RuleCondition(attribute="is_beta", operator=Operator.EQUALS, value=True)
                        ],
                        serve_value=True,
                    ),
                    TargetingRule(
                        name="Gradual Rollout 50%",
                        conditions=[],
                        serve_value=True,
                        rollout_percentage=50,
                    ),
                ],
            ),
            FlagCreate(
                key="checkout-redesign",
                name="One-Click Checkout Redesign",
                description="Streamlined checkout flow for mobile and desktop",
                flag_type=FlagType.STRING,
                enabled=True,
                default_value="legacy_v1",
                tags=["checkout", "growth"],
                rules=[
                    TargetingRule(
                        name="Internal Employees",
                        conditions=[
                            RuleCondition(attribute="email", operator=Operator.ENDS_WITH, value="@flagforge.dev")
                        ],
                        serve_value="variant_one_click",
                    ),
                    TargetingRule(
                        name="US and CA VIPs",
                        conditions=[
                            RuleCondition(attribute="country", operator=Operator.IN, value=["US", "CA"]),
                            RuleCondition(attribute="tier", operator=Operator.EQUALS, value="vip"),
                        ],
                        serve_value="variant_express",
                    ),
                ],
            ),
            FlagCreate(
                key="max-upload-size-mb",
                name="Maximum Upload Size Limit",
                description="Configurable file upload ceiling in megabytes",
                flag_type=FlagType.NUMBER,
                enabled=True,
                default_value=25,
                tags=["storage", "limits", "backend"],
                rules=[
                    TargetingRule(
                        name="Enterprise Plan",
                        conditions=[
                            RuleCondition(attribute="plan", operator=Operator.EQUALS, value="enterprise")
                        ],
                        serve_value=500,
                    ),
                    TargetingRule(
                        name="Pro Plan",
                        conditions=[
                            RuleCondition(attribute="plan", operator=Operator.EQUALS, value="pro")
                        ],
                        serve_value=100,
                    ),
                ],
            ),
            FlagCreate(
                key="beta-ai-copilot",
                name="AI Code Assistant Copilot",
                description="Generative AI suggestions during project setup",
                flag_type=FlagType.BOOLEAN,
                enabled=False,
                default_value=False,
                tags=["ai", "experimental"],
                rules=[],
            ),
        ]

        created_count = 0
        for flag_in in seed_flags:
            existing = await repo.get(flag_in.key)
            if not existing:
                await repo.create(flag_in)
                created_count += 1

        console.print(f"[green]Successfully seeded {created_count} flags to {settings.storage_file}[/green]")

    asyncio.run(_seed())


@main.command(name="list")
def list_cmd():
    async def _list():
        repo = InMemoryFlagRepository(settings.get_storage_path())
        flags, total = await repo.list(limit=200)

        table = Table(title=f"FlagForge Features ({total} flags)")
        table.add_column("Key", style="bold cyan")
        table.add_column("Name", style="white")
        table.add_column("Type", style="magenta")
        table.add_column("Status", style="bold")
        table.add_column("Default Value", style="yellow")
        table.add_column("Rules", justify="right")
        table.add_column("Tags", style="blue")

        for f in flags:
            status_str = "[green]ENABLED[/green]" if f.enabled else "[red]DISABLED[/red]"
            table.add_row(
                f.key,
                f.name,
                f.flag_type.value,
                status_str,
                str(f.default_value),
                str(len(f.rules)),
                ", ".join(f.tags),
            )

        console.print(table)

    asyncio.run(_list())


@main.command()
@click.argument("flag_key")
@click.option("--entity-id", default="anonymous-user", help="Entity or User ID")
@click.option("--attr", multiple=True, help="Attributes in key=val format (e.g. --attr plan=pro)")
def evaluate(flag_key: str, entity_id: str, attr: tuple[str, ...]):
    async def _evaluate():
        repo = InMemoryFlagRepository(settings.get_storage_path())
        flag = await repo.get(flag_key)
        if not flag:
            console.print(f"[bold red]Error:[/bold red] Flag '{flag_key}' not found.")
            return

        attributes: dict[str, str] = {}
        for item in attr:
            if "=" in item:
                k, v = item.split("=", 1)
                attributes[k.strip()] = v.strip()

        context = EvaluationContext(entity_id=entity_id, attributes=attributes)
        result = evaluate_flag(flag, context)

        table = Table(title=f"Evaluation Result: {flag_key}")
        table.add_column("Field", style="bold cyan")
        table.add_column("Value", style="yellow")

        table.add_row("Flag Key", result.flag_key)
        table.add_row("Evaluated Value", str(result.value))
        table.add_row("Enabled", str(result.enabled))
        table.add_row("Matched Rule ID", str(result.rule_id or "N/A"))
        table.add_row("Reason", result.reason)
        table.add_row("Entity ID", entity_id)
        table.add_row("Attributes", json.dumps(attributes))

        console.print(table)

    asyncio.run(_evaluate())


if __name__ == "__main__":
    main()
