import random
from typing import Any

FIRST_NAMES = [
    "  james  ",
    "MARY",
    "robert",
    "PATRICIA",
    "John   ",
    "  jennifer",
    "MICHAEL",
    "linda",
    "William",
    "ELIZABETH",
    "David",
    "barbara",
]

LAST_NAMES = [
    "SMITH",
    "  johnson",
    "Williams  ",
    "BROWN",
    "jones",
    "  Garcia  ",
    "MILLER",
    "davis",
    "Rodriguez",
    "MARTINEZ",
]

DOMAINS = [
    "example.com",
    "workmail.org",
    "techcorp.io",
    "globaldev.net",
]

CITIES = [
    "  NEW YORK  ",
    "los angeles",
    "CHICAGO",
    "  houston  ",
    "phoenix",
    "PHILADELPHIA",
    "san antonio",
    "SAN DIEGO",
    "dallas",
    "SAN JOSE",
]

RAW_DATES = [
    "2026/01/15",
    "15-01-2026",
    "01/15/2026",
    "Jan 15, 2026",
    "2026-01-15T08:30:00Z",
    "2026-03-22",
    "22/03/2026",
    "March 22, 2026",
]

RAW_PHONES = [
    "(555) 234-5678",
    "555.234.5678",
    "+15552345678",
    "5552345678",
    "555-234-5678",
    "(555) 987-6543",
    "555.987.6543",
    "+1 (555) 987-6543",
]

RAW_BALANCES = [
    "$1,250.50",
    "€2,500.00",
    "3,400.75",
    "$450.00",
    "£15,000.50",
    "$99,999,999.00",
    "  500.20  ",
    "$1,800.00",
]

RAW_BOOLEANS = [
    "yes",
    "Y",
    "true",
    "True",
    "1",
    "no",
    "N",
    "false",
    "False",
    "0",
]

MISSING_MARKERS = [
    "",
    "NA",
    "N/A",
    "null",
    "None",
    "-",
    "?",
]


def generate_dirty_dataset(row_count: int = 50) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for i in range(row_count):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        clean_first = first.strip().lower()
        clean_last = last.strip().lower()

        if random.random() < 0.1:
            email = f"invalid-email-{i}@"
        elif random.random() < 0.1:
            email = random.choice(MISSING_MARKERS)
        else:
            domain = random.choice(DOMAINS)
            email = f"  {clean_first}.{clean_last}{i}@{domain}  "

        phone = (
            random.choice(MISSING_MARKERS)
            if random.random() < 0.1
            else random.choice(RAW_PHONES)
        )
        date = (
            random.choice(MISSING_MARKERS)
            if random.random() < 0.08
            else random.choice(RAW_DATES)
        )
        balance = (
            random.choice(MISSING_MARKERS)
            if random.random() < 0.08
            else random.choice(RAW_BALANCES)
        )
        active = (
            random.choice(MISSING_MARKERS)
            if random.random() < 0.08
            else random.choice(RAW_BOOLEANS)
        )
        city = (
            random.choice(MISSING_MARKERS)
            if random.random() < 0.08
            else random.choice(CITIES)
        )

        row = {
            " Customer ID ": str(1000 + i),
            "First Name": first,
            "LAST_NAME": last,
            "e-mail address": email,
            "PHONE #": phone,
            "Sign up Date": date,
            "ACCOUNT_BALANCE": balance,
            " Is Active? ": active,
            "City": city,
        }
        rows.append(row)

    if len(rows) > 5:
        rows.append(dict(rows[1]))
        rows.append(dict(rows[3]))

    return rows
