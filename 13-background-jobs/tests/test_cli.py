from click.testing import CliRunner
from taskforge.cli import main


def test_cli_tasks_command():
    runner = CliRunner()
    result = runner.invoke(main, ["tasks"])
    assert result.exit_code == 0
    assert "send_email" in result.output
    assert "generate_report" in result.output


def test_cli_init_db_command():
    runner = CliRunner()
    result = runner.invoke(main, ["init-db"])
    assert result.exit_code == 0
    assert "initialized successfully" in result.output


def test_cli_enqueue_and_status():
    runner = CliRunner()
    runner.invoke(main, ["init-db"])

    result = runner.invoke(
        main,
        [
            "enqueue",
            "send_email",
            "-p",
            '{"to": "cli@test.com", "subject": "CLI"}',
            "--queue",
            "cli-queue",
        ],
    )
    assert result.exit_code == 0
    assert "Job Enqueued" in result.output
    assert "cli-queue" in result.output


def test_cli_enqueue_unregistered_task():
    runner = CliRunner()
    result = runner.invoke(main, ["enqueue", "non_existent_cli_task"])
    assert result.exit_code == 0
    assert "is not registered" in result.output


def test_cli_list_command():
    runner = CliRunner()
    result = runner.invoke(main, ["list"])
    assert result.exit_code == 0
    assert "TaskForge Jobs" in result.output


def test_cli_stats_command():
    runner = CliRunner()
    result = runner.invoke(main, ["stats"])
    assert result.exit_code == 0
    assert "Queue Metrics" in result.output
    assert "Active Workers" in result.output
