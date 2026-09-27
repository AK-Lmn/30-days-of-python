import pytest
from httpx import AsyncClient
from hookrelay.security.signer import compute_hmac_sha256


@pytest.mark.asyncio
async def test_health_endpoint(api_client: AsyncClient):
    response = await api_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "HookRelay"


@pytest.mark.asyncio
async def test_endpoint_crud(api_client: AsyncClient):
    create_payload = {
        "slug": "stripe-payments",
        "name": "Stripe Payments Hook",
        "verification_strategy": "stripe",
        "secret": "whsec_12345",
        "description": "Incoming payments from Stripe",
    }
    res = await api_client.post("/api/v1/endpoints", json=create_payload)
    assert res.status_code == 201
    ep = res.json()
    assert ep["slug"] == "stripe-payments"
    ep_id = ep["id"]

    res_dup = await api_client.post("/api/v1/endpoints", json=create_payload)
    assert res_dup.status_code == 409

    res_get = await api_client.get(f"/api/v1/endpoints/{ep_id}")
    assert res_get.status_code == 200
    assert res_get.json()["slug"] == "stripe-payments"

    res_list = await api_client.get("/api/v1/endpoints")
    assert res_list.status_code == 200
    assert any(item["id"] == ep_id for item in res_list.json())

    res_patch = await api_client.patch(
        f"/api/v1/endpoints/{ep_id}",
        json={"name": "Stripe Payments Updated"},
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["name"] == "Stripe Payments Updated"

    res_del = await api_client.delete(f"/api/v1/endpoints/{ep_id}")
    assert res_del.status_code == 204

    res_notfound = await api_client.get(f"/api/v1/endpoints/{ep_id}")
    assert res_notfound.status_code == 404


@pytest.mark.asyncio
async def test_subscription_crud(api_client: AsyncClient):
    sub_payload = {
        "name": "Slack Notifier",
        "target_url": "https://hooks.slack.com/services/T00/B00/X00",
        "event_patterns": ["alert.*", "error.*"],
        "max_retries": 4,
    }
    res = await api_client.post("/api/v1/subscriptions", json=sub_payload)
    assert res.status_code == 201
    sub = res.json()
    assert sub["name"] == "Slack Notifier"
    sub_id = sub["id"]

    res_get = await api_client.get(f"/api/v1/subscriptions/{sub_id}")
    assert res_get.status_code == 200
    assert res_get.json()["max_retries"] == 4

    res_patch = await api_client.patch(
        f"/api/v1/subscriptions/{sub_id}",
        json={"max_retries": 5},
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["max_retries"] == 5

    res_del = await api_client.delete(f"/api/v1/subscriptions/{sub_id}")
    assert res_del.status_code == 204


@pytest.mark.asyncio
async def test_ingest_api_flow(api_client: AsyncClient):
    ep_payload = {
        "slug": "github-push",
        "name": "GitHub Push Receiver",
        "verification_strategy": "github",
        "secret": "my_gh_secret",
    }
    ep_res = await api_client.post("/api/v1/endpoints", json=ep_payload)
    assert ep_res.status_code == 201

    body = b'{"ref": "refs/heads/main", "commits": [1]}'
    hex_sig = compute_hmac_sha256(body, "my_gh_secret")

    bad_sig_res = await api_client.post(
        "/api/v1/ingest/github-push",
        content=body,
        headers={"X-Hub-Signature-256": "sha256=invalid"},
    )
    assert bad_sig_res.status_code == 401

    good_res = await api_client.post(
        "/api/v1/ingest/github-push",
        content=body,
        headers={
            "X-Hub-Signature-256": f"sha256={hex_sig}",
            "X-GitHub-Event": "push",
            "X-GitHub-Delivery": "gh-delivery-uuid-99",
            "Content-Type": "application/json",
        },
    )
    assert good_res.status_code == 202
    event_data = good_res.json()
    assert event_data["is_duplicate"] is False
    assert event_data["event_type"] == "push"
    evt_id = event_data["event_id"]

    dup_res = await api_client.post(
        "/api/v1/ingest/github-push",
        content=body,
        headers={
            "X-Hub-Signature-256": f"sha256={hex_sig}",
            "X-GitHub-Delivery": "gh-delivery-uuid-99",
            "Content-Type": "application/json",
        },
    )
    assert dup_res.status_code == 200
    assert dup_res.json()["is_duplicate"] is True
    assert dup_res.json()["event_id"] == evt_id

    events_res = await api_client.get("/api/v1/events")
    assert events_res.status_code == 200
    assert any(e["id"] == evt_id for e in events_res.json())

    evt_details = await api_client.get(f"/api/v1/events/{evt_id}")
    assert evt_details.status_code == 200
    assert evt_details.json()["idempotency_key"] == "gh-delivery-uuid-99"

    deliveries_res = await api_client.get(f"/api/v1/events/{evt_id}/deliveries")
    assert deliveries_res.status_code == 200

    all_delivs_res = await api_client.get("/api/v1/deliveries")
    assert all_delivs_res.status_code == 200

    process_res = await api_client.post("/api/v1/deliveries/process-retries")
    assert process_res.status_code == 200
