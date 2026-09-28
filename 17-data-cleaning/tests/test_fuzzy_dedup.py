from cleanforge.cleaners.base import CleanContext
from cleanforge.cleaners.duplicates import DuplicateCleaner
from cleanforge.models.types import DuplicateKeep


def test_fuzzy_dedup_detects_near_matches() -> None:
    cleaner = DuplicateCleaner(
        fuzzy=True,
        similarity_threshold=0.80,
        fuzzy_columns=["company_name"],
        keep=DuplicateKeep.FIRST,
    )
    rows = [
        {"id": 1, "company_name": "Acme Technologies Inc"},
        {"id": 2, "company_name": "Acme Technologies Incorporated"},
        {"id": 3, "company_name": "Globex International"},
        {"id": 4, "company_name": "Acme Technologies Inc."},
    ]
    context = CleanContext()
    result = cleaner.clean(rows, context)

    assert len(result) == 2
    assert result[0]["company_name"] == "Acme Technologies Inc"
    assert result[1]["company_name"] == "Globex International"
    assert context.dropped_duplicates == 2


def test_fuzzy_dedup_handles_empty_fields() -> None:
    cleaner = DuplicateCleaner(
        fuzzy=True,
        similarity_threshold=0.85,
        fuzzy_columns=["title"],
    )
    rows = [
        {"id": 1, "title": ""},
        {"id": 2, "title": ""},
        {"id": 3, "title": "Developer"},
    ]
    context = CleanContext()
    result = cleaner.clean(rows, context)

    assert len(result) == 3
