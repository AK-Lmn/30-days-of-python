from pathlib import Path
from typing import Any
from cleanforge.config import get_preset_recipe
from cleanforge.engine.builder import CleanBuilder
from cleanforge.engine.pipeline import CleanEngine
from cleanforge.models.recipe import ValidationRule
from cleanforge.models.types import CasingType, DuplicateKeep, ImputeStrategy


def test_clean_engine_with_preset(sample_raw_records: list[dict[str, Any]]) -> None:
    preset = get_preset_recipe("customer")
    engine = CleanEngine(recipe=preset)
    clean_rows, report, quarantined = engine.run(sample_raw_records)

    assert report.initial_rows == 5
    assert len(clean_rows) > 0
    assert len(quarantined) > 0
    assert report.initial_health_score <= report.final_health_score


def test_clean_builder_fluent_flow(tmp_path: Path) -> None:
    raw_data = [
        {" ID ": "1", " NAME ": " alice smith ", "SCORE": "92.5%", "PHONE": "(555) 123-4567"},
        {" ID ": "2", " NAME ": "BOB JONES", "SCORE": "85.0%", "PHONE": "555.987.6543"},
        {" ID ": "1", " NAME ": " alice smith ", "SCORE": "92.5%", "PHONE": "(555) 123-4567"},
    ]

    builder = CleanBuilder()
    builder.from_records(raw_data)
    builder.standardize_headers(casing=CasingType.SNAKE)
    builder.drop_duplicates(subset=["id"], keep=DuplicateKeep.FIRST)
    builder.clean_text(columns=["name"], strip=True, casing=CasingType.TITLE)
    builder.clean_numbers(columns=["score"], parse_percentage=True, decimals=2)
    builder.clean_phones(columns=["phone"], phone_format="e164")

    clean_rows, report, _ = builder.execute()

    assert len(clean_rows) == 2
    assert clean_rows[0]["name"] == "Alice Smith"
    assert clean_rows[0]["score"] == 0.93
    assert clean_rows[0]["phone"] == "+15551234567"
    assert report.dropped_duplicates == 1


def test_builder_save_and_report(tmp_path: Path) -> None:
    raw_data = [
        {"id": "1", "email": "good@test.com", "val": "100"},
        {"id": "2", "email": "bad-email", "val": "-50"},
    ]

    out_file = tmp_path / "out.csv"
    quarantine_file = tmp_path / "quarantine.csv"
    report_file = tmp_path / "report.md"

    builder = CleanBuilder()
    builder.from_records(raw_data)
    builder.clean_emails(columns=["email"], action_on_invalid="quarantine")
    builder.validate([ValidationRule(column="val", min_value=0.0)])

    report = builder.save(
        output_path=out_file,
        quarantine_path=quarantine_file,
        report_path=report_file,
    )

    assert out_file.exists()
    assert quarantine_file.exists()
    assert report_file.exists()
    assert report.final_rows == 1
    assert report.quarantined_rows == 1

    report_content = report_file.read_text(encoding="utf-8")
    assert "# CleanForge Remediation Audit Report" in report_content
