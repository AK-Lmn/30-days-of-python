import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_workflow_crud_lifecycle(client: AsyncClient):
    create_payload = {
        "name": "User Registration Welcome",
        "description": "Sends welcome email when user registers",
        "enabled": True,
        "trigger_type": "event",
        "trigger_config": {"event_name": "user.registered"},
        "conditions": [
            {"field": "event.tier", "operator": "equals", "value": "premium"}
        ],
        "steps": [
            {
                "step_order": 0,
                "step_name": "send_welcome",
                "action_type": "notification",
                "action_config": {
                    "recipient": "{{ event.email }}",
                    "channel": "email",
                    "message": "Welcome {{ event.username }}!",
                },
                "continue_on_error": False,
                "retry_count": 0,
                "retry_delay_seconds": 1.0,
            }
        ],
    }

    create_res = await client.post("/api/v1/workflows", json=create_payload)
    assert create_res.status_code == 201
    created_data = create_res.json()
    wf_id = created_data["id"]
    assert created_data["name"] == "User Registration Welcome"
    assert len(created_data["steps"]) == 1

    get_res = await client.get(f"/api/v1/workflows/{wf_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == wf_id

    list_res = await client.get("/api/v1/workflows")
    assert list_res.status_code == 200
    assert any(w["id"] == wf_id for w in list_res.json())

    update_payload = {"name": "Updated Registration Flow", "enabled": False}
    update_res = await client.put(f"/api/v1/workflows/{wf_id}", json=update_payload)
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Updated Registration Flow"
    assert update_res.json()["enabled"] is False

    toggle_res = await client.post(f"/api/v1/workflows/{wf_id}/toggle")
    assert toggle_res.status_code == 200
    assert toggle_res.json()["enabled"] is True

    delete_res = await client.delete(f"/api/v1/workflows/{wf_id}")
    assert delete_res.status_code == 204

    missing_res = await client.get(f"/api/v1/workflows/{wf_id}")
    assert missing_res.status_code == 404


@pytest.mark.asyncio
async def test_workflow_manual_trigger(client: AsyncClient):
    create_payload = {
        "name": "Immediate Greeter",
        "enabled": True,
        "trigger_type": "manual",
        "steps": [
            {
                "step_order": 0,
                "step_name": "greet",
                "action_type": "notification",
                "action_config": {
                    "recipient": "guest@test.local",
                    "channel": "console",
                    "message": "Hi {{ event.name }}",
                },
            }
        ],
    }
    create_res = await client.post("/api/v1/workflows", json=create_payload)
    wf_id = create_res.json()["id"]

    run_res = await client.post(f"/api/v1/workflows/{wf_id}/run", json={"payload": {"name": "Taylor"}})
    assert run_res.status_code == 200
    run_data = run_res.json()
    assert run_data["status"] == "completed"
    assert len(run_data["step_runs"]) == 1
    assert run_data["step_runs"][0]["output_data"]["message"] == "Hi Taylor"
