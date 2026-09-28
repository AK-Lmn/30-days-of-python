from typing import Any
from cleanforge.cleaners.base import CleanContext
from cleanforge.cleaners.booleans import BooleanCleaner
from cleanforge.cleaners.dates import DateCleaner
from cleanforge.cleaners.duplicates import DuplicateCleaner
from cleanforge.cleaners.emails import EmailCleaner
from cleanforge.cleaners.headers import HeaderCleaner
from cleanforge.cleaners.missing import MissingCleaner
from cleanforge.cleaners.numbers import NumberCleaner
from cleanforge.cleaners.outliers import OutlierCleaner
from cleanforge.cleaners.phones import PhoneCleaner
from cleanforge.cleaners.text import TextCleaner
from cleanforge.cleaners.validator import ValidationCleaner
from cleanforge.models.recipe import ValidationRule
from cleanforge.models.types import (
    CasingType,
    DuplicateKeep,
    ImputeStrategy,
    OutlierMethod,
    OutlierStrategy,
)


def test_header_cleaner_snake_casing() -> None:
    cleaner = HeaderCleaner(casing=CasingType.SNAKE)
    rows = [{" First Name ": "John", "LAST-NAME": "Doe", "e-mail address": "a@b.com"}]
    context = CleanContext()
    result = cleaner.clean(rows, context)

    assert "first_name" in result[0]
    assert "last_name" in result[0]
    assert "e_mail_address" in result[0]
    assert result[0]["first_name"] == "John"


def test_header_cleaner_renaming() -> None:
    cleaner = HeaderCleaner(rename_map={"email_address": "email"})
    rows = [{"Email Address": "test@test.com"}]
    context = CleanContext()
    result = cleaner.clean(rows, context)

    assert "email" in result[0]
    assert result[0]["email"] == "test@test.com"


def test_missing_cleaner_constant() -> None:
    cleaner = MissingCleaner(
        column_strategies={"status": (ImputeStrategy.CONSTANT, "unknown")}
    )
    rows = [{"id": "1", "status": ""}, {"id": "2", "status": "active"}]
    context = CleanContext()
    result = cleaner.clean(rows, context)

    assert result[0]["status"] == "unknown"
    assert result[1]["status"] == "active"
    assert context.imputed_values == 1


def test_missing_cleaner_mean_and_median() -> None:
    cleaner = MissingCleaner(
        column_strategies={
            "score": (ImputeStrategy.MEAN, None),
            "age": (ImputeStrategy.MEDIAN, None),
        }
    )
    rows = [
        {"score": "10", "age": "20"},
        {"score": "20", "age": "30"},
        {"score": "30", "age": "40"},
        {"score": "NA", "age": "None"},
    ]
    context = CleanContext()
    result = cleaner.clean(rows, context)

    assert result[3]["score"] == 20.0
    assert result[3]["age"] == 30.0


def test_missing_cleaner_forward_fill() -> None:
    cleaner = MissingCleaner(
        column_strategies={"category": (ImputeStrategy.FORWARD_FILL, None)}
    )
    rows = [
        {"id": 1, "category": "Electronics"},
        {"id": 2, "category": "NA"},
        {"id": 3, "category": "Books"},
    ]
    context = CleanContext()
    result = cleaner.clean(rows, context)

    assert result[1]["category"] == "Electronics"
    assert result[2]["category"] == "Books"


def test_missing_cleaner_drop_row() -> None:
    cleaner = MissingCleaner(
        column_strategies={"required_col": (ImputeStrategy.DROP_ROW, None)}
    )
    rows = [
        {"id": 1, "required_col": "exists"},
        {"id": 2, "required_col": "null"},
    ]
    context = CleanContext()
    result = cleaner.clean(rows, context)

    assert len(result) == 1
    assert result[0]["id"] == 1
    assert len(context.quarantined_rows) == 1


def test_duplicate_cleaner_exact() -> None:
    cleaner = DuplicateCleaner(subset=["email"], keep=DuplicateKeep.FIRST)
    rows = [
        {"id": 1, "email": "a@test.com", "val": 10},
        {"id": 2, "email": "a@test.com", "val": 20},
        {"id": 3, "email": "b@test.com", "val": 30},
    ]
    context = CleanContext()
    result = cleaner.clean(rows, context)

    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[1]["id"] == 3
    assert context.dropped_duplicates == 1


def test_duplicate_cleaner_keep_last() -> None:
    cleaner = DuplicateCleaner(subset=["email"], keep=DuplicateKeep.LAST)
    rows = [
        {"id": 1, "email": "a@test.com"},
        {"id": 2, "email": "a@test.com"},
    ]
    context = CleanContext()
    result = cleaner.clean(rows, context)

    assert len(result) == 1
    assert result[0]["id"] == 2


def test_text_cleaner_operations() -> None:
    cleaner = TextCleaner(
        columns=["name", "desc"],
        strip=True,
        collapse_spaces=True,
        casing=CasingType.TITLE,
        remove_html=True,
    )
    rows = [
        {
            "name": "  jOHN   dOE  ",
            "desc": "<b>awesome</b>   product",
        }
    ]
    context = CleanContext()
    result = cleaner.clean(rows, context)

    assert result[0]["name"] == "John Doe"
    assert result[0]["desc"] == "Awesome Product"


def test_number_cleaner() -> None:
    cleaner = NumberCleaner(
        columns=["price", "discount", "qty"],
        strip_currency=True,
        remove_commas=True,
        parse_percentage=True,
        decimals=2,
    )
    rows = [
        {
            "price": " $1,450.99 ",
            "discount": " 15% ",
            "qty": "42",
        }
    ]
    context = CleanContext()
    result = cleaner.clean(rows, context)

    assert result[0]["price"] == 1450.99
    assert result[0]["discount"] == 0.15
    assert result[0]["qty"] == 42.0


def test_date_cleaner() -> None:
    cleaner = DateCleaner(
        columns=["date1", "date2", "date3"],
        target_format="%Y-%m-%d",
    )
    rows = [
        {
            "date1": "15/01/2026",
            "date2": "Jan 15, 2026",
            "date3": "2026-01-15T12:00:00Z",
        }
    ]
    context = CleanContext()
    result = cleaner.clean(rows, context)

    assert result[0]["date1"] == "2026-01-15"
    assert result[0]["date2"] == "2026-01-15"
    assert result[0]["date3"] == "2026-01-15"


def test_boolean_cleaner() -> None:
    cleaner = BooleanCleaner(columns=["active", "verified"])
    rows = [
        {"active": "yes", "verified": "0"},
        {"active": "FALSE", "verified": "true"},
        {"active": "", "verified": None},
    ]
    context = CleanContext()
    result = cleaner.clean(rows, context)

    assert result[0]["active"] is True
    assert result[0]["verified"] is False
    assert result[1]["active"] is False
    assert result[1]["verified"] is True
    assert result[2]["active"] is None
    assert result[2]["verified"] is None


def test_phone_cleaner() -> None:
    cleaner = PhoneCleaner(columns=["phone"], phone_format="e164")
    rows = [
        {"phone": "(555) 234-5678"},
        {"phone": "555.234.5678"},
        {"phone": "+1 555 234 5678"},
    ]
    context = CleanContext()
    result = cleaner.clean(rows, context)

    for r in result:
        assert r["phone"] == "+15552345678"


def test_email_cleaner_quarantine() -> None:
    cleaner = EmailCleaner(columns=["email"], action_on_invalid="quarantine")
    rows = [
        {"id": 1, "email": "valid.user@test.org"},
        {"id": 2, "email": "bad-user@"},
    ]
    context = CleanContext()
    result = cleaner.clean(rows, context)

    assert len(result) == 1
    assert result[0]["id"] == 1
    assert len(context.quarantined_rows) == 1
    assert "Invalid email" in context.quarantined_rows[0]["_quarantine_reason"]


def test_outlier_cleaner_iqr_clip() -> None:
    cleaner = OutlierCleaner(
        columns=["val"],
        method=OutlierMethod.IQR,
        strategy=OutlierStrategy.CLIP,
        threshold=1.5,
    )
    rows = [
        {"val": 10},
        {"val": 12},
        {"val": 11},
        {"val": 13},
        {"val": 12},
        {"val": 1000},
    ]
    context = CleanContext()
    result = cleaner.clean(rows, context)

    assert result[-1]["val"] < 100
    assert context.outliers_handled == 1


def test_validation_cleaner_constraints() -> None:
    rules = [
        ValidationRule(column="age", min_value=0, max_value=120),
        ValidationRule(column="role", allowed_values=["admin", "user"]),
    ]
    cleaner = ValidationCleaner(rules)
    rows = [
        {"id": 1, "age": 25, "role": "admin"},
        {"id": 2, "age": 150, "role": "admin"},
        {"id": 3, "age": 30, "role": "guest"},
    ]
    context = CleanContext()
    result = cleaner.clean(rows, context)

    assert len(result) == 1
    assert result[0]["id"] == 1
    assert len(context.quarantined_rows) == 2


def test_header_cleaner_all_casing_styles() -> None:
    rows = [{"First Name": "A", "Last Name": "B"}]
    ctx = CleanContext()

    camel_res = HeaderCleaner(casing=CasingType.CAMEL).clean(rows, ctx)
    assert "firstName" in camel_res[0]

    kebab_res = HeaderCleaner(casing=CasingType.KEBAB).clean(rows, ctx)
    assert "first-name" in kebab_res[0]

    upper_res = HeaderCleaner(casing=CasingType.UPPER).clean(rows, ctx)
    assert "FIRST NAME" in upper_res[0]

    lower_res = HeaderCleaner(casing=CasingType.LOWER).clean(rows, ctx)
    assert "first name" in lower_res[0]


def test_number_cleaner_european_format() -> None:
    cleaner = NumberCleaner(columns=["amt"], decimals=2)
    rows = [{"amt": "1.234,56 €"}]
    context = CleanContext()
    res = cleaner.clean(rows, context)
    assert res[0]["amt"] == 1234.56


def test_outlier_cleaner_zscore_and_strategies() -> None:
    cleaner_drop = OutlierCleaner(
        columns=["score"],
        method=OutlierMethod.ZSCORE,
        strategy=OutlierStrategy.DROP,
        threshold=2.0,
    )
    rows = [
        {"score": 50},
        {"score": 52},
        {"score": 48},
        {"score": 51},
        {"score": 49},
        {"score": 50},
        {"score": 500},
    ]
    context = CleanContext()
    res_drop = cleaner_drop.clean(rows, context)
    assert len(res_drop) == 6
    assert len(context.quarantined_rows) == 1

    cleaner_null = OutlierCleaner(
        columns=["score"],
        method=OutlierMethod.IQR,
        strategy=OutlierStrategy.NULLIFY,
    )
    res_null = cleaner_null.clean(rows, CleanContext())
    assert res_null[-1]["score"] is None


def test_validation_cleaner_regex_and_not_null() -> None:
    rules = [
        ValidationRule(column="sku", regex_pattern=r"^SKU-\d{4}$"),
        ValidationRule(column="sku", not_null=True),
    ]
    cleaner = ValidationCleaner(rules)
    rows = [
        {"sku": "SKU-1234"},
        {"sku": "INVALID"},
        {"sku": ""},
    ]
    context = CleanContext()
    res = cleaner.clean(rows, context)
    assert len(res) == 1
    assert res[0]["sku"] == "SKU-1234"
    assert len(context.quarantined_rows) == 2
