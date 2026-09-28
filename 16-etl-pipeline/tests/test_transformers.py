from pipeforge.models.record import Record
from pipeforge.transformers.normalizers import (
    StringCleaner,
    CaseNormalizer,
    DateNormalizer,
    TypeCaster,
)
from pipeforge.transformers.mappers import (
    FieldRenamer,
    FieldPicker,
    FieldRemover,
    DerivedField,
    ValueMapper,
    RecordFilter,
)
from pipeforge.transformers.anonymizer import FieldAnonymizer
from pipeforge.transformers.deduplicator import Deduplicator
from pipeforge.transformers.aggregator import BatchAggregator
from pipeforge.transformers.chain import TransformerChain


def test_string_cleaner() -> None:
    cleaner = StringCleaner(fields=["text", "status"], strip_whitespace=True, collapse_spaces=True)
    rec = Record.from_raw({"text": "  hello   world  ", "status": " N/A "})
    res = cleaner.transform(rec)
    assert res is not None
    assert res.data["text"] == "hello world"
    assert res.data["status"] is None


def test_case_normalizer() -> None:
    norm = CaseNormalizer(fields=["city", "code"], mode="lower")
    rec = Record.from_raw({"city": "NEW YORK", "code": "ABC-123"})
    res = norm.transform(rec)
    assert res is not None
    assert res.data["city"] == "new york"
    assert res.data["code"] == "abc-123"


def test_date_normalizer() -> None:
    norm = DateNormalizer(fields=["date"], output_format="%Y-%m-%d")
    rec = Record.from_raw({"date": "09/28/2026"})
    res = norm.transform(rec)
    assert res is not None
    assert res.data["date"] == "2026-09-28"


def test_type_caster() -> None:
    caster = TypeCaster({"qty": int, "price": float, "active": bool})
    rec = Record.from_raw({"qty": "15", "price": "19.99", "active": "yes"})
    res = caster.transform(rec)
    assert res is not None
    assert res.data["qty"] == 15
    assert res.data["price"] == 19.99
    assert res.data["active"] is True


def test_field_renamer_and_picker() -> None:
    renamer = FieldRenamer({"old_title": "title"})
    picker = FieldPicker(["id", "title"])
    rec = Record.from_raw({"id": 1, "old_title": "Item A", "temp_col": 99})

    chain = TransformerChain([renamer, picker])
    res = chain.transform(rec)
    assert res is not None
    assert res.data == {"id": 1, "title": "Item A"}


def test_derived_field() -> None:
    derive = DerivedField("total", lambda row: row["price"] * row["qty"])
    rec = Record.from_raw({"price": 10.5, "qty": 3})
    res = derive.transform(rec)
    assert res is not None
    assert res.data["total"] == 31.5


def test_value_mapper() -> None:
    mapper = ValueMapper("status", {"p": "pending", "c": "completed"}, default="unknown")
    rec = Record.from_raw({"status": "p"})
    res = mapper.transform(rec)
    assert res is not None
    assert res.data["status"] == "pending"


def test_record_filter() -> None:
    filter_step = RecordFilter(lambda r: r.data.get("age", 0) >= 18)
    adult = Record.from_raw({"name": "Adult", "age": 20})
    minor = Record.from_raw({"name": "Minor", "age": 15})

    assert filter_step.transform(adult) is not None
    assert filter_step.transform(minor) is None


def test_anonymizer() -> None:
    anonymizer = FieldAnonymizer(fields=["email"], strategy="mask_email")
    rec = Record.from_raw({"email": "john.doe@example.com"})
    res = anonymizer.transform(rec)
    assert res is not None
    assert res.data["email"].startswith("j")
    assert res.data["email"].endswith("@example.com")
    assert "*" in res.data["email"]


def test_deduplicator() -> None:
    dedup = Deduplicator(key_fields=["id"])
    rec1 = Record.from_raw({"id": 1, "val": "A"})
    rec2 = Record.from_raw({"id": 1, "val": "Duplicate"})
    rec3 = Record.from_raw({"id": 2, "val": "B"})

    assert dedup.transform(rec1) is not None
    assert dedup.transform(rec2) is None
    assert dedup.transform(rec3) is not None


def test_batch_aggregator() -> None:
    records = [
        Record.from_raw({"category": "A", "sales": 10}),
        Record.from_raw({"category": "A", "sales": 20}),
        Record.from_raw({"category": "B", "sales": 30}),
    ]
    agg = BatchAggregator(
        group_by=["category"],
        aggregations={
            "total_sales": ("sales", "sum"),
            "order_count": ("sales", "count"),
        },
    )
    results = agg.aggregate(records)
    assert len(results) == 2

    cat_a = next(r for r in results if r.data["category"] == "A")
    assert cat_a.data["total_sales"] == 30.0
    assert cat_a.data["order_count"] == 2
