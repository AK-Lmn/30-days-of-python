import pytest
from starlette.testclient import TestClient
from flagforge.main import create_app
from flagforge.repositories.memory import InMemoryFlagRepository, InMemoryAuditRepository, MetricsTracker


@pytest.fixture
def app():
    test_app = create_app(persistence_path=None)
    test_app.state.flag_repo = InMemoryFlagRepository(persistence_path=None)
    test_app.state.audit_repo = InMemoryAuditRepository()
    test_app.state.metrics_tracker = MetricsTracker()
    return test_app


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_flag_data():
    return {
        "key": "new-checkout-flow",
        "name": "New Checkout Flow",
        "description": "Redesigned streamlined checkout modal",
        "flag_type": "boolean",
        "enabled": True,
        "default_value": False,
        "tags": ["checkout", "web"],
        "rules": [
            {
                "id": "rule-beta",
                "name": "Beta Users",
                "conditions": [
                    {
                        "attribute": "is_beta",
                        "operator": "equals",
                        "value": True,
                    }
                ],
                "serve_value": True,
            }
        ],
    }
