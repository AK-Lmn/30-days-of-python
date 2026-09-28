from pathlib import Path
from click.testing import CliRunner
from cleanforge.cli import main
from cleanforge.io.writer import DatasetWriter


def test_cli_sample_and_inspect(tmp_path: Path) -> None:
    runner = CliRunner()
    sample_file = tmp_path / "sample.csv"

    gen_result = runner.invoke(
        main, ["sample", "-n", "10", "-o", str(sample_file)]
    )
    assert gen_result.exit_code == 0
    assert sample_file.exists()

    inspect_result = runner.invoke(main, ["inspect", str(sample_file)])
    assert inspect_result.exit_code == 0
    assert "CleanForge Inspector" in inspect_result.output
    assert "Health Score" in inspect_result.output


def test_cli_clean_and_diff(tmp_path: Path) -> None:
    runner = CliRunner()
    raw_file = tmp_path / "dirty.csv"
    out_file = tmp_path / "clean.csv"
    quarantine_file = tmp_path / "quarantine.csv"
    report_file = tmp_path / "report.md"

    data = [
        {" Customer ID ": "1", "First Name": " alice ", "e-mail address": "alice@test.com"},
        {" Customer ID ": "2", "First Name": "bob", "e-mail address": "invalid-email"},
        {" Customer ID ": "1", "First Name": " alice ", "e-mail address": "alice@test.com"},
    ]
    writer = DatasetWriter()
    writer.write(data, raw_file)

    clean_result = runner.invoke(
        main,
        [
            "clean",
            str(raw_file),
            "-o",
            str(out_file),
            "-p",
            "customer",
            "-q",
            str(quarantine_file),
            "--report",
            str(report_file),
        ],
    )
    assert clean_result.exit_code == 0
    assert out_file.exists()
    assert quarantine_file.exists()
    assert report_file.exists()

    diff_result = runner.invoke(main, ["diff", str(raw_file), str(out_file)])
    assert diff_result.exit_code == 0
    assert "Before vs After Quality Comparison" in diff_result.output


def test_cli_recipe_init(tmp_path: Path) -> None:
    runner = CliRunner()
    recipe_file = tmp_path / "recipe.yaml"

    init_result = runner.invoke(
        main, ["recipe-init", "-p", "ecommerce", "-o", str(recipe_file)]
    )
    assert init_result.exit_code == 0
    assert recipe_file.exists()
    content = recipe_file.read_text(encoding="utf-8")
    assert "ecommerce_cleaning_recipe" in content
