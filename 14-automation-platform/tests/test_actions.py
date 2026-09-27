import os
from pathlib import Path
import pytest
from autoflow.actions.delay import DelayAction
from autoflow.actions.file_ops import FileAppendAction, FileWriteAction
from autoflow.actions.http import HttpAction
from autoflow.actions.notification import NotificationAction
from autoflow.actions.transform import TransformAction


@pytest.mark.asyncio
async def test_notification_action():
    action = NotificationAction()
    res = await action.execute(
        {"recipient": "team@example.com", "channel": "slack", "message": "Deploy ready"},
        {},
    )
    assert res["delivered"] is True
    assert res["recipient"] == "team@example.com"
    assert res["channel"] == "slack"
    assert res["message"] == "Deploy ready"


@pytest.mark.asyncio
async def test_transform_action():
    action = TransformAction()
    context = {"event": {"user_id": 42, "role": "admin", "secret": "abc"}}
    config = {
        "mapping": {"uid": "event.user_id", "display": "User {{ event.user_id }}"},
        "pick_keys": ["role"],
        "set_constants": {"platform": "autoflow"},
    }
    res = await action.execute(config, context)
    data = res["result"]
    assert data["uid"] == 42
    assert data["display"] == "User 42"
    assert data["role"] == "admin"
    assert data["platform"] == "autoflow"


@pytest.mark.asyncio
async def test_file_ops_actions(tmp_path: Path):
    target_file = tmp_path / "test_output.log"
    write_action = FileWriteAction()
    append_action = FileAppendAction()

    res_write = await write_action.execute({"path": str(target_file), "content": "Line 1"}, {})
    assert res_write["bytes_written"] > 0
    assert target_file.read_text(encoding="utf-8") == "Line 1"

    res_append = await append_action.execute({"path": str(target_file), "content": "Line 2"}, {})
    assert res_append["bytes_appended"] > 0
    assert target_file.read_text(encoding="utf-8") == "Line 1\nLine 2\n"


@pytest.mark.asyncio
async def test_delay_action():
    action = DelayAction()
    res = await action.execute({"seconds": 0.01}, {})
    assert res["delayed_seconds"] == 0.01


@pytest.mark.asyncio
async def test_http_action_missing_url():
    action = HttpAction()
    with pytest.raises(ValueError, match="HTTP action requires 'url'"):
        await action.execute({}, {})
