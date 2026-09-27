from autoflow.engine.templating import extract_context_value, render_template_value


def test_extract_context_value_nested():
    context = {
        "event": {
            "user": {
                "id": "u-123",
                "profile": {"email": "user@example.com"},
            },
            "count": 42,
        },
        "trigger": {"type": "event"},
    }

    assert extract_context_value("event.user.id", context) == "u-123"
    assert extract_context_value("event.user.profile.email", context) == "user@example.com"
    assert extract_context_value("event.count", context) == 42
    assert extract_context_value("trigger.type", context) == "event"
    assert extract_context_value("nonexistent.path", context) is None


def test_render_template_value_string():
    context = {
        "event": {
            "name": "Jane",
            "order_id": 999,
        }
    }

    res = render_template_value("Hello {{ event.name }} - Order ID: {{ event.order_id }}", context)
    assert res == "Hello Jane - Order ID: 999"


def test_render_template_value_native_types():
    context = {
        "event": {
            "amount": 150,
            "is_vip": True,
            "items": ["a", "b"],
        }
    }

    assert render_template_value("{{ event.amount }}", context) == 150
    assert render_template_value("{{ event.is_vip }}", context) is True
    assert render_template_value("{{ event.items }}", context) == ["a", "b"]


def test_render_template_value_nested_structures():
    context = {
        "event": {
            "username": "alex",
            "score": 10,
        }
    }
    input_payload = {
        "user": "{{ event.username }}",
        "points": "{{ event.score }}",
        "tags": ["user-{{ event.username }}", 100],
    }

    output = render_template_value(input_payload, context)
    assert output == {
        "user": "alex",
        "points": 10,
        "tags": ["user-alex", 100],
    }
