import pytest
from api_cli.filter import FilterError, apply_jmespath_filter, filter_payload, pick_fields


def test_apply_jmespath_filter_basic():
    data = {"users": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]}
    result = apply_jmespath_filter(data, "users[*].name")
    assert result == ["Alice", "Bob"]


def test_apply_jmespath_filter_conditional():
    data = {
        "items": [
            {"id": 1, "active": True},
            {"id": 2, "active": False},
            {"id": 3, "active": True},
        ]
    }
    result = apply_jmespath_filter(data, "items[?active].id")
    assert result == [1, 3]


def test_apply_jmespath_filter_empty_expression():
    data = {"key": "value"}
    assert apply_jmespath_filter(data, "") == data
    assert apply_jmespath_filter(data, "   ") == data


def test_apply_jmespath_filter_invalid_expression():
    data = {"key": "value"}
    with pytest.raises(FilterError):
        apply_jmespath_filter(data, "items[invalid!syntax")


def test_pick_fields_list_of_dicts():
    data = [
        {"id": 1, "name": "Alice", "role": "admin", "secret": "123"},
        {"id": 2, "name": "Bob", "role": "user", "secret": "456"},
    ]
    result = pick_fields(data, ["id", "name"])
    assert result == [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
    ]


def test_pick_fields_single_dict():
    data = {"id": 10, "username": "ckzz", "email": "test@example.com", "token": "abc"}
    result = pick_fields(data, ["id", "username"])
    assert result == {"id": 10, "username": "ckzz"}


def test_pick_fields_empty():
    data = {"id": 1}
    assert pick_fields(data, []) == data


def test_filter_payload_combined():
    data = {
        "data": [
            {"id": 1, "status": "active", "score": 90, "extra": "omit"},
            {"id": 2, "status": "inactive", "score": 40, "extra": "omit"},
            {"id": 3, "status": "active", "score": 85, "extra": "omit"},
        ]
    }
    result = filter_payload(data, expression="data[?status=='active']", fields=["id", "score"])
    assert result == [
        {"id": 1, "score": 90},
        {"id": 3, "score": 85},
    ]
