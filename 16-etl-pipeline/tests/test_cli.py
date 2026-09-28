from pathlib import Path
from click.testing import CliRunner
from pipeforge.cli import main


def test_cli_version() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_cli_sample_data(tmp_path: Path) -> None:
    runner = CliRunner()
    orders_csv = tmp_path / "orders.csv"
    res1 = runner.invoke(main, ["sample-data", "--type", "orders", "--count", "20", "--output", str(orders_csv)])
    assert res1.exit_code == 0
    assert orders_csv.exists()

    users_json = tmp_path / "users.json"
    res2 = runner.invoke(main, ["sample-data", "--type", "users", "--count", "15", "--output", str(users_json)])
    assert res2.exit_code == 0
    assert users_json.exists()


def test_cli_inspect(tmp_path: Path) -> None:
    runner = CliRunner()
    data_csv = tmp_path / "test.csv"
    data_csv.write_text("id,name,amount\n1,Alpha,100\n2,Beta,\n", encoding="utf-8")

    res = runner.invoke(main, ["inspect", "--source", str(data_csv), "--rows", "2"])
    assert res.exit_code == 0
    assert "Column Profiling" in res.output
    assert "Total Rows: 2" in res.output


def test_cli_run_quick(tmp_path: Path) -> None:
    runner = CliRunner()
    data_csv = tmp_path / "quick.csv"
    data_csv.write_text("id,val\n1,A\n2,B\n", encoding="utf-8")
    out_csv = tmp_path / "out.csv"

    res = runner.invoke(main, ["run", "--source", str(data_csv), "--dest", str(out_csv)])
    assert res.exit_code == 0
    assert "Pipeline Execution Summary" in res.output
    assert out_csv.exists()


def test_cli_run_yaml(tmp_path: Path) -> None:
    runner = CliRunner()
    src_csv = tmp_path / "in.csv"
    src_csv.write_text("id,val\n10,foo\n", encoding="utf-8")
    out_json = tmp_path / "out.json"

    yaml_text = f"""
name: "cli_yaml_test"
source:
  type: "csv"
  path: "{str(src_csv).replace('\\', '/')}"
destinations:
  - type: "json"
    path: "{str(out_json).replace('\\', '/')}"
"""
    cfg_file = tmp_path / "test.yaml"
    cfg_file.write_text(yaml_text, encoding="utf-8")

    res = runner.invoke(main, ["run", "--config", str(cfg_file)])
    assert res.exit_code == 0
    assert out_json.exists()


def test_cli_history_and_quarantine(tmp_path: Path) -> None:
    runner = CliRunner()
    audit_db = tmp_path / "audit.db"
    db_url = f"sqlite:///{audit_db}"

    src_csv = tmp_path / "dirty.csv"
    src_csv.write_text("id,email\n1,bad_email\n", encoding="utf-8")
    out_csv = tmp_path / "out.csv"

    yaml_text = f"""
name: "quarantine_cli_test"
error_strategy: "QUARANTINE"
source:
  type: "csv"
  path: "{str(src_csv).replace('\\', '/')}"
validation:
  rules:
    - type: "email"
      field: "email"
destinations:
  - type: "csv"
    path: "{str(out_csv).replace('\\', '/')}"
"""
    cfg_file = tmp_path / "test.yaml"
    cfg_file.write_text(yaml_text, encoding="utf-8")

    runner.invoke(main, ["run", "--config", str(cfg_file)])

    hist_res = runner.invoke(main, ["history"])
    assert hist_res.exit_code == 0
