import json
import sqlite3
from pathlib import Path
import pytest
from pipeforge.engine.pipeline import ETLPipeline, PipelineError
from pipeforge.engine.yaml_parser import PipelineConfigParser
from pipeforge.extractors.csv_extractor import CsvExtractor
from pipeforge.extractors.json_extractor import JsonExtractor
from pipeforge.loaders.csv_loader import CsvLoader
from pipeforge.loaders.database_loader import DatabaseLoader
from pipeforge.validators.rules import EmailRule, RuleValidator
from pipeforge.validators.quality_gate import QualityGate
from pipeforge.transformers.normalizers import StringCleaner, CaseNormalizer
from pipeforge.transformers.mappers import DerivedField
from pipeforge.transformers.aggregator import BatchAggregator
from pipeforge.storage.audit_store import AuditStore
from pipeforge.models.enums import ErrorStrategy, PipelineStatus, LoadMode


def test_pipeline_run_success(tmp_path: Path) -> None:
    src_csv = tmp_path / "input.csv"
    src_csv.write_text("id,name,email\n1,Alice,alice@example.com\n2,Bob,bob@example.com\n", encoding="utf-8")

    out_csv = tmp_path / "output.csv"
    audit_db = tmp_path / "audit.db"

    extractor = CsvExtractor(src_csv)
    loader = CsvLoader(out_csv, mode=LoadMode.REPLACE)
    validator = RuleValidator([EmailRule("email")])
    transformer = CaseNormalizer(fields=["name"], mode="upper")
    audit_store = AuditStore(f"sqlite:///{audit_db}")

    pipeline = ETLPipeline(
        name="test_pipeline",
        extractor=extractor,
        loaders=[loader],
        validators=[validator],
        transformers=[transformer],
        audit_store=audit_store,
        error_strategy=ErrorStrategy.QUARANTINE,
    )

    metrics = pipeline.run()

    assert metrics.records_read == 2
    assert metrics.records_valid == 2
    assert metrics.records_loaded == 2
    assert metrics.records_quarantined == 0

    run_record = audit_store.get_run(pipeline.run_id)
    assert run_record is not None
    assert run_record.status == PipelineStatus.SUCCESS.value


def test_pipeline_quarantine_strategy(tmp_path: Path) -> None:
    src_csv = tmp_path / "input_dirty.csv"
    src_csv.write_text("id,email\n1,valid@example.com\n2,invalid-email\n", encoding="utf-8")

    out_csv = tmp_path / "output.csv"
    audit_db = tmp_path / "audit.db"

    extractor = CsvExtractor(src_csv)
    loader = CsvLoader(out_csv, mode=LoadMode.REPLACE)
    validator = RuleValidator([EmailRule("email")])
    audit_store = AuditStore(f"sqlite:///{audit_db}")

    pipeline = ETLPipeline(
        name="quarantine_pipeline",
        extractor=extractor,
        loaders=[loader],
        validators=[validator],
        audit_store=audit_store,
        error_strategy=ErrorStrategy.QUARANTINE,
    )

    metrics = pipeline.run()

    assert metrics.records_read == 2
    assert metrics.records_valid == 1
    assert metrics.records_loaded == 1
    assert metrics.records_quarantined == 1

    quarantined = audit_store.get_quarantined_records(pipeline.run_id)
    assert len(quarantined) == 1
    assert quarantined[0].row_number == 2


def test_pipeline_fail_fast_strategy(tmp_path: Path) -> None:
    src_csv = tmp_path / "input_fail.csv"
    src_csv.write_text("id,email\n1,invalid-email\n", encoding="utf-8")

    extractor = CsvExtractor(src_csv)
    loader = CsvLoader(tmp_path / "out.csv")
    validator = RuleValidator([EmailRule("email")])

    pipeline = ETLPipeline(
        name="fail_fast_pipeline",
        extractor=extractor,
        loaders=[loader],
        validators=[validator],
        error_strategy=ErrorStrategy.FAIL_FAST,
    )

    with pytest.raises(PipelineError):
        pipeline.run()


def test_pipeline_skip_strategy(tmp_path: Path) -> None:
    src_csv = tmp_path / "input_skip.csv"
    src_csv.write_text("id,email\n1,invalid-email\n2,valid@test.com\n", encoding="utf-8")

    out_csv = tmp_path / "output.csv"
    pipeline = ETLPipeline(
        name="skip_pipeline",
        extractor=CsvExtractor(src_csv),
        loaders=[CsvLoader(out_csv)],
        validators=[RuleValidator([EmailRule("email")])],
        error_strategy=ErrorStrategy.SKIP,
    )

    metrics = pipeline.run()
    assert metrics.records_read == 2
    assert metrics.records_skipped == 1
    assert metrics.records_loaded == 1


def test_pipeline_aggregation(tmp_path: Path) -> None:
    src_json = tmp_path / "sales.json"
    data = [
        {"dept": "Engineering", "amount": 100},
        {"dept": "Engineering", "amount": 200},
        {"dept": "Sales", "amount": 150},
    ]
    src_json.write_text(json.dumps(data), encoding="utf-8")

    out_csv = tmp_path / "dept_summary.csv"
    agg = BatchAggregator(
        group_by=["dept"],
        aggregations={"total": ("amount", "sum"), "count": ("amount", "count")},
    )

    pipeline = ETLPipeline(
        name="agg_pipeline",
        extractor=JsonExtractor(src_json),
        loaders=[CsvLoader(out_csv)],
        aggregator=agg,
    )

    metrics = pipeline.run()
    assert metrics.records_read == 3
    assert metrics.records_loaded == 2


def test_yaml_parser(tmp_path: Path) -> None:
    src_csv = tmp_path / "src.csv"
    src_csv.write_text("id,qty,price\n1,2,10.0\n", encoding="utf-8")
    out_csv = tmp_path / "out.csv"

    config_content = f"""
name: "yaml_test_pipe"
source:
  type: "csv"
  path: "{str(src_csv).replace('\\', '/')}"
validation:
  rules:
    - type: "not_empty"
      field: "id"
transformations:
  - type: "cast"
    types:
      qty: "int"
      price: "float"
  - type: "derive"
    field: "total"
    expression: "price * qty"
destinations:
  - type: "csv"
    path: "{str(out_csv).replace('\\', '/')}"
    mode: "REPLACE"
"""
    cfg_file = tmp_path / "pipeline.yaml"
    cfg_file.write_text(config_content, encoding="utf-8")

    pipeline = PipelineConfigParser.from_yaml_file(cfg_file)
    metrics = pipeline.run()

    assert metrics.records_read == 1
    assert metrics.records_loaded == 1
    assert out_csv.exists()
