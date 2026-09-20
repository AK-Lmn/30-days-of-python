from fastapi.testclient import TestClient
from api_aggregator.server import app

client = TestClient(app)


def test_server_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "/health" in data["endpoints"]


def test_server_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "providers" in data


def test_server_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "total_requests" in data
    assert "cache_hits" in data


def test_server_news_endpoint():
    response = client.get("/api/v1/aggregate/news?limit=2&force_mock=true")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("SUCCESS", "PARTIAL")
    assert "data" in data
    assert len(data["data"]) <= 2


def test_server_crypto_endpoint():
    response = client.get(
        "/api/v1/aggregate/crypto?symbols=BTC,ETH&force_mock=true"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("SUCCESS", "PARTIAL")
    assert len(data["data"]) == 2


def test_server_weather_endpoint():
    response = client.get("/api/v1/aggregate/weather?city=Paris&force_mock=true")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("SUCCESS", "PARTIAL")
    assert data["data"]["location"] == "Paris"


def test_server_overview_endpoint():
    response = client.get("/api/v1/aggregate/overview?force_mock=true")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("SUCCESS", "PARTIAL")
    assert "top_news" in data["data"]
    assert "crypto_rates" in data["data"]


def test_server_custom_endpoint():
    payload = {
        "urls": ["https://api.test/v1", "https://api.test/v2"],
        "timeout_seconds": 2.0,
    }
    response = client.post(
        "/api/v1/aggregate/custom?force_mock=true", json=payload
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 2


def test_server_cache_clear_endpoint():
    response = client.delete("/api/v1/cache")
    assert response.status_code == 200
    assert response.json()["status"] == "cleared"
