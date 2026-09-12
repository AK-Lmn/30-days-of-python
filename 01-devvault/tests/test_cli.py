import json
from pathlib import Path
from click.testing import CliRunner
import pytest

from devvault.cli import cli


@pytest.fixture
def runner(tmp_path: Path):
    db_path = str(tmp_path / "cli_vault.db")

    class CustomRunner:
        def invoke(self, args, **kwargs):
            cli_args = ["--db", db_path] + args
            r = CliRunner()
            return r.invoke(cli, cli_args, **kwargs)

    return CustomRunner()


def test_cli_add_and_list(runner):
    res = runner.invoke([
        "add",
        "-t", "Hello Script",
        "-T", "snippet",
        "-c", "print('hello')",
        "-l", "python",
    ])
    assert res.exit_code == 0
    assert "Saved snippet #1" in res.output

    list_res = runner.invoke(["list"])
    assert list_res.exit_code == 0
    assert "Hello Script" in list_res.output
    assert "SNIPPET" in list_res.output


def test_cli_add_stdin(runner):
    res = runner.invoke(
        ["add", "-t", "Piped Snippet", "-T", "snippet", "--stdin", "-l", "bash"],
        input="echo 'piped'\n",
    )
    assert res.exit_code == 0
    assert "Saved snippet" in res.output

    show_res = runner.invoke(["show", "1"])
    assert show_res.exit_code == 0
    assert "piped" in show_res.output


def test_cli_shorthand_commands(runner):
    res_cmd = runner.invoke(["cmd", "add", "Docker PS", "docker ps -a"])
    assert res_cmd.exit_code == 0
    assert "Saved command" in res_cmd.output

    res_url = runner.invoke(["url", "add", "Python Org", "https://python.org"])
    assert res_url.exit_code == 0
    assert "Saved url" in res_url.output

    res_note = runner.invoke(["note", "add", "Meeting Notes", "Discussed roadmap"])
    assert res_note.exit_code == 0
    assert "Saved note" in res_note.output


def test_cli_search(runner):
    runner.invoke(["cmd", "add", "Git Log Pretty", "git log --oneline --graph"])
    runner.invoke(["note", "add", "Grocery List", "Milk, Eggs, Bread"])

    search_res = runner.invoke(["search", "Git Log"])
    assert search_res.exit_code == 0
    assert "Git Log Pretty" in search_res.output
    assert "Grocery List" not in search_res.output

    filtered_search = runner.invoke(["search", "Git", "-t", "command"])
    assert filtered_search.exit_code == 0
    assert "Git Log Pretty" in filtered_search.output


def test_cli_show_and_copy(runner, monkeypatch):
    runner.invoke(["cmd", "add", "Copy Target", "echo copy-me"])

    copied_text = []
    monkeypatch.setattr("devvault.cli.pyperclip.copy", lambda text: copied_text.append(text))

    res = runner.invoke(["copy", "1"])
    assert res.exit_code == 0
    assert "Copied #1" in res.output
    assert copied_text == ["echo copy-me"]

    res_show = runner.invoke(["show", "1", "--copy"])
    assert res_show.exit_code == 0
    assert "Copied content to clipboard" in res_show.output


def test_cli_run_command(runner):
    runner.invoke(["cmd", "add", "Echo Test", "echo testing_cli_run"])

    res = runner.invoke(["run", "1", "--yes"])
    assert res.exit_code == 0
    assert "testing_cli_run" in res.output
    assert "Finished executing successfully" in res.output


def test_cli_edit_and_delete(runner):
    runner.invoke(["note", "add", "Initial", "initial content"])

    edit_res = runner.invoke(["edit", "1", "-t", "Updated Title", "-c", "new content"])
    assert edit_res.exit_code == 0
    assert "Updated item #1" in edit_res.output

    show_res = runner.invoke(["show", "1"])
    assert "Updated Title" in show_res.output
    assert "new content" in show_res.output

    del_res = runner.invoke(["delete", "1", "--yes"])
    assert del_res.exit_code == 0
    assert "Deleted item #1" in del_res.output

    del_verify = runner.invoke(["show", "1"])
    assert del_verify.exit_code != 0
    assert "not found" in del_verify.output


def test_cli_stats(runner):
    runner.invoke(["cmd", "add", "C1", "cmd1"])
    runner.invoke(["note", "add", "N1", "note1"])

    stats_res = runner.invoke(["stats"])
    assert stats_res.exit_code == 0
    assert "Total Entries" in stats_res.output


def test_cli_export_and_import(runner, tmp_path: Path):
    runner.invoke(["cmd", "add", "Exported Cmd", "ls -la"])
    export_file = str(tmp_path / "export.json")

    exp_res = runner.invoke(["export", "-f", "json", "-o", export_file])
    assert exp_res.exit_code == 0
    assert Path(export_file).exists()

    new_db_file = str(tmp_path / "import_target.db")
    imp_runner = CliRunner()
    imp_res = imp_runner.invoke(cli, ["--db", new_db_file, "import", export_file])
    assert imp_res.exit_code == 0
    assert "Successfully imported 1 items" in imp_res.output
