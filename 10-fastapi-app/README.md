# Day 10 — FlagForge: Feature Flag & Configuration API

A production-grade, asynchronous REST API for dynamic feature flag management and real-time rule evaluation built with FastAPI, Pydantic v2, and Python 3.13.

**Date:** Sep 21, 2026  
**Status:** ✅ Completed

---

## Overview

FlagForge allows software engineering teams to decouple deployment from release. It enables toggling features in real-time, executing percentage-based canary rollouts, targeting specific user segments through multi-condition rules, maintaining a tamper-evident audit history, and tracking evaluation metrics.

### Key Highlights

- **FastAPI Architecture**: Fully asynchronous route handlers, dependency injection, and lifespan resource management.
- **Dynamic Rule Evaluation Engine**:
  - Operators: `equals`, `not_equals`, `contains`, `in`, `not_in`, `greater_than`, `less_than`, `starts_with`, `ends_with`.
  - Deterministic user bucketing: SHA-256 hash modulo 100 ensures consistent percentage rollouts for any given user ID.
  - Granular multivariate support: Boolean flags, string variants, numeric thresholds, and JSON configurations.
- **RESTful Endpoints & Schema Standards**:
  - Consistent pagination metadata (`offset`, `limit`, `total`, `has_more`).
  - Standardized error envelope with structured error codes (`FLAG_NOT_FOUND`, `FLAG_ALREADY_EXISTS`, `VALIDATION_ERROR`, etc.).
  - Request ID propagation (`X-Request-ID`) and high-resolution latency tracking (`X-Process-Time-Ms`).
- **Comprehensive Audit Log**: Automatic history recording every flag creation, update, state toggle, and deletion.
- **Developer Experience**:
  - Interactive OpenAPI / Swagger UI at `/docs` and ReDoc at `/redoc`.
  - Rich interactive CLI for running the server, seeding sample flags, listing registered flags, and evaluating context rules directly in the terminal.
  - Complete automated test suite using `pytest` with 100% pass rate.

---

## Repository Structure

```text
10-fastapi-app/
├── pyproject.toml              # Build config and project dependencies
├── requirements.txt            # Locked requirements
├── README.md                   # Project documentation
├── .gitignore
├── data/
│   └── flags.json              # Local persistent JSON state
├── flagforge/
│   ├── __init__.py
│   ├── main.py                 # Application factory, middleware, and exception handlers
│   ├── config.py               # Environment configuration via Pydantic Settings
│   ├── dependencies.py         # Request-scoped dependency injection
│   ├── cli.py                  # Click and Rich command-line interface
│   ├── core/
│   │   ├── __init__.py
│   │   ├── errors.py           # Domain error hierarchy
│   │   ├── middleware.py       # Latency and request ID middleware
│   │   └── evaluator.py        # Rule matching and percentage hashing engine
│   ├── models/
│   │   ├── __init__.py
│   │   ├── common.py           # Pagination and error envelope schemas
│   │   ├── flag.py             # Flag, rule, condition, and toggle models
│   │   ├── evaluation.py       # Single and bulk evaluation request/response models
│   │   ├── audit.py            # Audit log entry and action models
│   │   └── metrics.py          # System telemetry and health models
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── base.py             # Repository protocol interfaces
│   │   └── memory.py           # Thread-safe repository with JSON persistence
│   └── routers/
│       ├── __init__.py
│       ├── health.py           # /, /health, /metrics
│       ├── flags.py            # /api/v1/flags CRUD and toggle endpoints
│       ├── evaluations.py      # /api/v1/evaluate and /api/v1/evaluate-all
│       └── audit.py            # /api/v1/audit-logs query endpoint
└── tests/
    ├── __init__.py
    ├── conftest.py             # Pytest fixtures and test client setup
    ├── test_evaluator.py       # Unit tests for rule condition engine & hashing
    ├── test_flags_api.py       # Integration tests for flag lifecycle & pagination
    ├── test_evaluation_api.py  # Integration tests for single and bulk evaluation
    ├── test_audit_api.py       # Integration tests for audit log tracking
    └── test_health_api.py      # Integration tests for health and middleware
```

---

## Getting Started

### 1. Installation

Using `uv` (recommended):

```powershell
uv venv .venv
uv pip install -e .[dev]
```

Or standard `pip`:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Seed Sample Flags

Populate demo feature flags into the repository:

```powershell
uv run flagforge seed
```

### 3. List Registered Flags

```powershell
uv run flagforge list
```

### 4. Evaluate Flags via CLI

Evaluate against different user contexts:

```powershell
# Matches the internal employee rule
uv run flagforge evaluate checkout-redesign --entity-id usr-100 --attr email=alex@flagforge.dev

# Falls back to default value
uv run flagforge evaluate checkout-redesign --entity-id usr-200 --attr email=guest@example.com
```

### 5. Launch the REST API Server

```powershell
uv run flagforge serve --port 8000
```

Once running:
- **Interactive Documentation (Swagger UI)**: `http://localhost:8000/docs`
- **Alternative Documentation (ReDoc)**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

---

## API Reference

### System Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | API service metadata and route directory |
| `GET` | `/health` | Service health status and uptime |
| `GET` | `/metrics` | Flag totals, evaluation counts, and telemetry |

### Flags Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/flags` | List flags (supports `tag`, `search`, `enabled`, `offset`, `limit`) |
| `POST` | `/api/v1/flags` | Create a new flag (`201 Created` or `409 Conflict`) |
| `GET` | `/api/v1/flags/{key}` | Retrieve flag details |
| `PUT` | `/api/v1/flags/{key}` | Update flag parameters, rules, and tags |
| `PATCH` | `/api/v1/flags/{key}/toggle` | Fast toggle flag enabled state |
| `DELETE` | `/api/v1/flags/{key}` | Delete flag (`204 No Content`) |

### Evaluation Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/evaluate` | Evaluate a single flag against user context |
| `POST` | `/api/v1/evaluate-all` | Evaluate all or specified flags in bulk |

### Audit Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/audit-logs` | Query change events with optional `flag_key` filter |

---

## Example API Requests

### 1. Create a Feature Flag

```bash
curl -X POST "http://localhost:8000/api/v1/flags" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "new-billing-portal",
    "name": "New Billing Portal",
    "description": "Self-service invoice and subscription management",
    "flag_type": "boolean",
    "enabled": true,
    "default_value": false,
    "tags": ["billing", "finance"],
    "rules": [
      {
        "name": "Enterprise Users",
        "conditions": [
          {
            "attribute": "tier",
            "operator": "equals",
            "value": "enterprise"
          }
        ],
        "serve_value": true
      }
    ]
  }'
```

### 2. Evaluate Flag for Context

```bash
curl -X POST "http://localhost:8000/api/v1/evaluate" \
  -H "Content-Type: application/json" \
  -d '{
    "flag_key": "new-billing-portal",
    "context": {
      "entity_id": "cust-8821",
      "attributes": {
        "tier": "enterprise"
      }
    }
  }'
```

Response:
```json
{
  "flag_key": "new-billing-portal",
  "value": true,
  "enabled": true,
  "rule_id": "c62b5d4e",
  "reason": "RULE_MATCH",
  "evaluated_at": "2026-09-21T10:15:00.000000Z"
}
```

### 3. Bulk Evaluation

```bash
curl -X POST "http://localhost:8000/api/v1/evaluate-all" \
  -H "Content-Type: application/json" \
  -d '{
    "context": {
      "entity_id": "user-449",
      "attributes": {
        "is_beta": true
      }
    }
  }'
```

---

## Testing & Verification

Run the full automated test suite:

```powershell
uv run pytest -v
```

Output:
```text
tests/test_audit_api.py::test_audit_logs_lifecycle PASSED
tests/test_audit_api.py::test_audit_logs_filtered_by_key PASSED
tests/test_evaluation_api.py::test_evaluate_single_rule_match PASSED
tests/test_evaluation_api.py::test_evaluate_single_default_value PASSED
tests/test_evaluation_api.py::test_evaluate_single_fallback_on_missing PASSED
tests/test_evaluation_api.py::test_evaluate_single_missing_error PASSED
tests/test_evaluation_api.py::test_evaluate_bulk PASSED
tests/test_evaluator.py::test_compute_rollout_bucket_deterministic PASSED
tests/test_evaluator.py::test_evaluate_condition_equals PASSED
tests/test_evaluator.py::test_evaluate_condition_not_equals PASSED
tests/test_evaluator.py::test_evaluate_condition_contains PASSED
tests/test_evaluator.py::test_evaluate_condition_in_and_not_in PASSED
tests/test_evaluator.py::test_evaluate_condition_numeric_comparisons PASSED
tests/test_evaluator.py::test_evaluate_condition_string_boundary PASSED
tests/test_evaluator.py::test_evaluate_flag_disabled_returns_default PASSED
tests/test_evaluator.py::test_evaluate_flag_rules_match PASSED
tests/test_evaluator.py::test_evaluate_flag_percentage_rollout PASSED
tests/test_flags_api.py::test_list_flags_empty PASSED
tests/test_flags_api.py::test_create_and_get_flag PASSED
tests/test_flags_api.py::test_create_flag_duplicate_conflict PASSED
tests/test_flags_api.py::test_create_flag_invalid_key_validation PASSED
tests/test_flags_api.py::test_get_flag_not_found PASSED
tests/test_flags_api.py::test_update_flag PASSED
tests/test_flags_api.py::test_toggle_flag PASSED
tests/test_flags_api.py::test_delete_flag PASSED
tests/test_flags_api.py::test_list_flags_filtering_and_pagination PASSED
tests/test_health_api.py::test_root_endpoint PASSED
tests/test_health_api.py::test_health_endpoint PASSED
tests/test_health_api.py::test_metrics_endpoint PASSED

29 passed in 0.45s
```
