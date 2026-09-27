import json
from pathlib import Path
from click.testing import CliRunner

from autoflow.cli import actions, init_sample, main, stats, workflow


def test_cli_actions_command():
    runner = CliRunner()
    result = runner.invoke(actions)
    assert result.exit_code == 0
    assert "http_request" in result.output
    assert "transform" in result.output


def test_cli_init_sample_and_workflow_list():
    runner = CliRunner()
    sample_res = runner.invoke(init_sample)
    assert sample_res.exit_code == 0
    assert "Sample" in sample_res.output

    list_res = runner.invoke(workflow, ["list"])
    assert list_res.exit_code == 0
    assert "Configured Automations" in list_res.output


def test_cli_workflow_create_from_file(tmp_path: Path):
    flow_file = tmp_path / "flow.json"
    content = {
        "name": "CLI Created Flow",
        "description": "Created via CLI file",
        "enabled": True,
        "trigger_type": "manual",
        "trigger_config": {},
        "conditions": [],
        "steps": [
            {
                "step_order": 0,
                "step_name": "notify_step",
                "action_type": "notification",
                "action_config": {"recipient": "cli@test.com", "message": "hello"},
            }
        ],
    }
    flow_file.write_text(json.dumps(content), encoding="utf-8")

    runner = CliRunner()
    res = runner.invoke(workflow, ["create", "-f", str(flow_file)])
    assert res.exit_code == 0
    assert "created with ID" in res.output


def test_cli_stats():
    runner = CliRunner()
    res = runner.invoke(stats)
    assert res.exit_code == 0
    assert "Platform Statistics" in res.output
