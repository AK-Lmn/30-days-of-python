import uuid
from click.testing import CliRunner
from hookrelay.cli import main


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "endpoint" in result.output
    assert "subscription" in result.output
    assert "event" in result.output
    assert "delivery" in result.output
    assert "simulate" in result.output


def test_cli_endpoint_commands(tmp_path):
    db_file = tmp_path / "test_ep.db"
    env = {"HOOKRELAY_DATABASE_URL": f"sqlite+aiosqlite:///{db_file}", "COLUMNS": "200"}
    runner = CliRunner(env=env)

    slug = f"ep-{uuid.uuid4().hex[:8]}"
    create_res = runner.invoke(
        main,
        [
            "endpoint",
            "create",
            slug,
            "CLI Endpoint",
            "--strategy",
            "token",
            "--secret",
            "cli_secret",
            "--description",
            "Created from test",
        ],
    )
    assert create_res.exit_code == 0
    assert "Endpoint created:" in create_res.output

    list_res = runner.invoke(main, ["endpoint", "list"])
    assert list_res.exit_code == 0
    assert slug in list_res.output


def test_cli_subscription_commands(tmp_path):
    db_file = tmp_path / "test_sub.db"
    env = {"HOOKRELAY_DATABASE_URL": f"sqlite+aiosqlite:///{db_file}", "COLUMNS": "200"}
    runner = CliRunner(env=env)

    create_res = runner.invoke(
        main,
        [
            "subscription",
            "create",
            "CLI-Subscription",
            "http://example.com/cli",
            "--pattern",
            "order.*",
            "--retries",
            "5",
        ],
    )
    assert create_res.exit_code == 0
    assert "Subscription created:" in create_res.output

    list_res = runner.invoke(main, ["subscription", "list"])
    assert list_res.exit_code == 0
    assert "CLI-Subscription" in list_res.output


def test_cli_simulate_and_event_commands(tmp_path):
    db_file = tmp_path / "test_sim.db"
    env = {"HOOKRELAY_DATABASE_URL": f"sqlite+aiosqlite:///{db_file}", "COLUMNS": "200"}
    runner = CliRunner(env=env)

    slug = f"sim-{uuid.uuid4().hex[:8]}"
    runner.invoke(
        main,
        [
            "endpoint",
            "create",
            slug,
            "Sim Endpoint",
            "--strategy",
            "none",
        ],
    )

    key = f"key-{uuid.uuid4().hex[:8]}"
    sim_res = runner.invoke(
        main,
        [
            "simulate",
            slug,
            "--type",
            "order.created",
            "--payload",
            '{"id": 555, "status": "paid"}',
            "--idempotency-key",
            key,
        ],
    )
    assert sim_res.exit_code == 0
    assert "Simulated event ingested successfully:" in sim_res.output

    events_res = runner.invoke(main, ["event", "list"])
    assert events_res.exit_code == 0
    assert "order.created" in events_res.output

    deliveries_res = runner.invoke(main, ["delivery", "list"])
    assert deliveries_res.exit_code == 0

    retries_res = runner.invoke(main, ["delivery", "process-retries"])
    assert retries_res.exit_code == 0
    assert "Processed" in retries_res.output
