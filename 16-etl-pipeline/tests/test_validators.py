import pytest
from pydantic import BaseModel, Field
from pipeforge.models.record import Record
from pipeforge.models.metrics import PipelineMetrics
from pipeforge.validators.rules import (
    NotEmptyRule,
    RangeRule,
    RegexRule,
    EmailRule,
    InListRule,
    RuleValidator,
)
from pipeforge.validators.schema_validator import SchemaValidator
from pipeforge.validators.quality_gate import QualityGate


def test_rules_not_empty() -> None:
    rule = NotEmptyRule("username")
    assert rule.evaluate("alice")[0] is True
    assert rule.evaluate("")[0] is False
    assert rule.evaluate(None)[0] is False


def test_rules_range() -> None:
    rule = RangeRule("score", min_value=0.0, max_value=100.0)
    assert rule.evaluate(50)[0] is True
    assert rule.evaluate(0)[0] is True
    assert rule.evaluate(100)[0] is True
    assert rule.evaluate(-1)[0] is False
    assert rule.evaluate(101)[0] is False
    assert rule.evaluate("invalid")[0] is False


def test_rules_regex() -> None:
    rule = RegexRule("sku", r"^PROD-\d{4}$")
    assert rule.evaluate("PROD-1234")[0] is True
    assert rule.evaluate("PROD-123")[0] is False
    assert rule.evaluate("INVALID")[0] is False


def test_rules_email() -> None:
    rule = EmailRule("email")
    assert rule.evaluate("test@example.com")[0] is True
    assert rule.evaluate("not-an-email")[0] is False
    assert rule.evaluate("user@domain")[0] is False


def test_rules_in_list() -> None:
    rule = InListRule("status", ["pending", "active", "completed"])
    assert rule.evaluate("active")[0] is True
    assert rule.evaluate("deleted")[0] is False


def test_rule_validator_combined() -> None:
    validator = RuleValidator([
        NotEmptyRule("name"),
        EmailRule("email"),
        RangeRule("age", min_value=18),
    ])

    valid_record = Record.from_raw({"name": "Alice", "email": "alice@test.com", "age": 25})
    validator.validate(valid_record)
    assert valid_record.is_valid is True

    invalid_record = Record.from_raw({"name": "", "email": "bad", "age": 15})
    validator.validate(invalid_record)
    assert invalid_record.is_valid is False
    assert len(invalid_record.errors) == 3


class CustomerSchema(BaseModel):
    id: int
    name: str
    email: str
    active: bool = True


def test_schema_validator_pydantic() -> None:
    validator = SchemaValidator(CustomerSchema)

    valid_record = Record.from_raw({"id": "123", "name": "Bob", "email": "bob@test.com"})
    validator.validate(valid_record)
    assert valid_record.is_valid is True
    assert valid_record.data["id"] == 123
    assert valid_record.data["active"] is True

    invalid_record = Record.from_raw({"id": "not-an-int", "name": "Bob"})
    validator.validate(invalid_record)
    assert invalid_record.is_valid is False
    assert len(invalid_record.errors) > 0


def test_schema_validator_dict() -> None:
    validator = SchemaValidator({"val": int, "label": str})
    rec = Record.from_raw({"val": "42", "label": "Test"})
    validator.validate(rec)
    assert rec.is_valid is True
    assert rec.data["val"] == 42


def test_quality_gate() -> None:
    gate = QualityGate(
        max_error_rate=0.10,
        min_records=2,
        max_null_percentage={"email": 0.0},
        unique_fields=["id"],
    )

    metrics = PipelineMetrics(records_read=5, records_invalid=0)
    records = [
        Record.from_raw({"id": 1, "email": "a@test.com"}),
        Record.from_raw({"id": 2, "email": "b@test.com"}),
    ]
    passed, violations = gate.evaluate(metrics, records)
    assert passed is True
    assert len(violations) == 0

    bad_metrics = PipelineMetrics(records_read=10, records_invalid=3)
    passed_bad, violations_bad = gate.evaluate(bad_metrics, records)
    assert passed_bad is False
    assert any("Error rate" in v for v in violations_bad)
