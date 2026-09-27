import uuid
from click.testing import CliRunner
from wardenauth.cli import cli
from wardenauth.core.tokens import create_access_token


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_cli_inspect_token():
    token = create_access_token(
        user_id="test-cli-user",
        role="admin",
        scopes=["*"],
        session_id="cli-session-123",
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["inspect-token", token])
    assert result.exit_code == 0
    assert "test-cli-user" in result.output
    assert "admin" in result.output


def test_cli_create_user_and_list_and_stats():
    runner = CliRunner()
    unique_suffix = uuid.uuid4().hex[:6]
    username = f"cli_{unique_suffix}"
    email = f"{username}@example.com"

    create_res = runner.invoke(
        cli,
        [
            "create-user",
            "--email",
            email,
            "--username",
            username,
            "--password",
            "CliPassword123!",
            "--role",
            "admin",
        ],
    )
    assert create_res.exit_code == 0
    assert "User created successfully" in create_res.output

    list_res = runner.invoke(cli, ["list-users"], env={"COLUMNS": "160"})
    assert list_res.exit_code == 0
    assert username in list_res.output

    issue_res = runner.invoke(cli, ["issue-token", username], env={"COLUMNS": "160"})
    assert issue_res.exit_code == 0
    assert "Issued Access Token" in issue_res.output

    stats_res = runner.invoke(cli, ["stats"], env={"COLUMNS": "160"})
    assert stats_res.exit_code == 0
    assert "Total Users" in stats_res.output

    audit_res = runner.invoke(cli, ["audit-logs"], env={"COLUMNS": "160"})
    assert audit_res.exit_code == 0
    assert "Audit Logs" in audit_res.output
