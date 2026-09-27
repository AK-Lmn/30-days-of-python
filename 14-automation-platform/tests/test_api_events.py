import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_event_ingest_and_trigger_flow(client: AsyncClient):
    create_payload = {
        "name": "Invoice Paid Listener",
        "enabled": True,
        "trigger_type": "event",
        "trigger_config": {"event_name": "invoice.paid"},
        "conditions": [],
        "steps": [
            {
                "step_order": 0,
                "step_name": "notify_finance",
                "action_type": "notification",
                "action_config": {
                    "recipient": "finance@example.com",
                    "message": "Invoice {{ event.invoice_id }} paid for ${{ event.amount }}",
                },
            }
        ],
    }
    wf_res = await client.post("/api/v1/workflows", json=create_payload)
    assert wf_res.status_code == 201
    wf_id = wf_res.json()["id"]

    event_payload = {
        "event_name": "invoice.paid",
        "payload": {"invoice_id": "INV-1001", "amount": 450},
    }
    event_res = await client.post("/api/v1/events", json=event_payload)
    assert event_res.status_code == 202
    event_data = event_res.json()
    assert event_data["event_name"] == "invoice.paid"
    assert wf_id in event_data["matched_workflows"]
    assert len(event_data["runs_triggered"]) == 1

    run_id = event_data["runs_triggered"][0]
    run_res = await client.get(f"/api/v1/runs/{run_id}")
    assert run_res.status_code == 200
    run_detail = run_res.json()
    assert run_detail["status"] == "completed"
    assert run_detail["step_runs"][0]["output_data"]["message"] == "Invoice INV-1001 paid for $450"

    events_list_res = await client.get("/api/v1/events")
    assert events_list_res.status_code == 200
    assert any(e["event_name"] == "invoice.paid" for e in events_list_res.json())
