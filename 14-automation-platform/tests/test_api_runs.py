import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_api_runs_and_stats(client: AsyncClient):
    create_payload = {
        "name": "Audit Logging",
        "enabled": True,
        "trigger_type": "manual",
        "steps": [
            {
                "step_order": 0,
                "step_name": "log_entry",
                "action_type": "notification",
                "action_config": {
                    "recipient": "audit@internal.net",
                    "message": "Audit event",
                },
            }
        ],
    }
    wf_res = await client.post("/api/v1/workflows", json=create_payload)
    wf_id = wf_res.json()["id"]

    run_res = await client.post(f"/api/v1/workflows/{wf_id}/run", json={"payload": {}})
    run_id = run_res.json()["id"]

    runs_res = await client.get("/api/v1/runs")
    assert runs_res.status_code == 200
    runs_data = runs_res.json()
    assert any(r["id"] == run_id for r in runs_data)

    detail_res = await client.get(f"/api/v1/runs/{run_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["workflow_id"] == wf_id

    cancel_res = await client.post(f"/api/v1/runs/{run_id}/cancel")
    assert cancel_res.status_code == 400

    actions_res = await client.get("/api/v1/actions")
    assert actions_res.status_code == 200
    actions = actions_res.json()
    assert any(a["action_type"] == "http_request" for a in actions)
    assert any(a["action_type"] == "transform" for a in actions)

    health_res = await client.get("/health")
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "healthy"

    stats_res = await client.get("/api/v1/stats")
    assert stats_res.status_code == 200
    assert stats_res.json()["total_workflows"] >= 1
