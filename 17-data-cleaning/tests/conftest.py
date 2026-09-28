from typing import Any
import pytest


@pytest.fixture
def sample_raw_records() -> list[dict[str, Any]]:
    return [
        {
            " Customer ID ": "101",
            "Full Name": "  john doe  ",
            "Email Address": "  JOHN.DOE@EXAMPLE.COM  ",
            "Phone": "(555) 123-4567",
            "Signup Date": "2026/01/15",
            "Balance": "$1,250.50",
            "Is Active": "yes",
            "Score": "95.5",
        },
        {
            " Customer ID ": "102",
            "Full Name": "JANE SMITH",
            "Email Address": "jane.smith@example.org",
            "Phone": "555.987.6543",
            "Signup Date": "15-01-2026",
            "Balance": "€2,500.00",
            "Is Active": "1",
            "Score": "88.0",
        },
        {
            " Customer ID ": "103",
            "Full Name": "Bob   Jones",
            "Email Address": "invalid-email@",
            "Phone": "+15551112233",
            "Signup Date": "Jan 15, 2026",
            "Balance": "N/A",
            "Is Active": "no",
            "Score": "999.0",
        },
        {
            " Customer ID ": "101",
            "Full Name": "  john doe  ",
            "Email Address": "  JOHN.DOE@EXAMPLE.COM  ",
            "Phone": "(555) 123-4567",
            "Signup Date": "2026/01/15",
            "Balance": "$1,250.50",
            "Is Active": "yes",
            "Score": "95.5",
        },
        {
            " Customer ID ": "104",
            "Full Name": "Alice Brown",
            "Email Address": "alice@brown.com",
            "Phone": "None",
            "Signup Date": "2026-01-15T00:00:00Z",
            "Balance": "$500.00",
            "Is Active": "true",
            "Score": "75.0",
        },
    ]
