# Day 14 — AutoFlow: Enterprise Automation Platform

An event-driven and scheduled automation engine built with Python, FastAPI, SQLAlchemy, and Click. AutoFlow empowers developers to define multi-step reactive workflows triggered by incoming webhooks/events, cron schedules, or manual dispatch.

**Date:** Sep 25, 2026  
**Status:** ✅ Complete  

---

## Architecture Overview

```
               ┌────────────────────────────────────────────────────────┐
               │                    Trigger Sources                     │
               │  [Schedule / Cron]   [Event / Webhook]   [Manual API]  │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │                   AutoFlow Platform                    │
               │                                                        │
               │   1. Trigger Matching & Rule Condition Evaluation      │
               │   2. Dynamic Template Engine (Context Interpolation)    │
               │   3. Action Dispatcher & Execution Pipeline            │
               │   4. State & Observability Persistence (Async SQLite)  │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │                    Pluggable Actions                   │
               │  [HTTP Webhook]  [Notification]  [Transform]           │
               │  [File Write]    [File Append]   [Async Delay]         │
               └────────────────────────────────────────────────────────┘
```

---

## Key Features

1. **Multi-Step Workflows**
   - Sequential action execution pipelines with configurable order.
   - Per-step retry configurations with exponential/custom backoff.
   - `continue_on_error` support for fault-tolerant automation chains.

2. **Trigger Support**
   - **Event-Driven**: Match incoming events (`order.created`, `user.registered`, or wildcards `*`).
   - **Scheduled / Cron**: Periodic intervals (`interval_seconds: 30`) or standard 5-part cron expressions (`cron: "*/5 * * * *"`).
   - **Manual**: On-demand execution with arbitrary input payloads.

3. **Condition & Filter Rules**
   - Flexible rule predicates evaluated before workflow execution:
     - `equals`, `not_equals`
     - `greater_than`, `greater_than_or_equal`, `less_than`, `less_than_or_equal`
     - `contains`, `not_contains`
     - `starts_with`, `ends_with`
     - `is_null`, `is_not_null`
     - `matches_regex`

4. **Action Catalog**
   - `http_request`: Send external HTTP requests (GET, POST, PUT, DELETE, PATCH).
   - `notification`: Dispatch alert messages via email, Slack, or console.
   - `transform`: Map, project, and reshape JSON keys and constants.
   - `file_write`: Write formatted payloads to designated local paths.
   - `file_append`: Atomically append structured logs or records.
   - `delay`: Asynchronous sleep and rate pacing.

5. **Context Variable Interpolation**
   - Downstream steps consume outputs from previous steps:
     - `{{ event.customer_name }}`
     - `{{ steps.enrich_step.result.tier }}`
     - `{{ trigger.workflow_name }}`
   - Native type preservation for integers, booleans, and collections.

6. **Execution Observability**
   - Full execution histories tracked in `workflow_runs` and `step_runs`.
   - Per-step timing in milliseconds, output payloads, and detailed error messages.
   - Ingested event audit log.

7. **FastAPI REST API & Rich CLI**
   - Full CRUD REST API with OpenAPI documentation at `/docs`.
   - Rich interactive CLI with formatted tables, execution details, and server management.

---

## Directory Layout

```text
14-automation-platform/
├── autoflow/
│   ├── actions/
│   │   ├── base.py
│   │   ├── delay.py
│   │   ├── file_ops.py
│   │   ├── http.py
│   │   ├── notification.py
│   │   └── transform.py
│   ├── engine/
│   │   ├── conditions.py
│   │   ├── executor.py
│   │   ├── registry.py
│   │   ├── scheduler.py
│   │   └── templating.py
│   ├── models/
│   │   ├── db_models.py
│   │   ├── enums.py
│   │   └── schemas.py
│   ├── repositories/
│   │   ├── run_repo.py
│   │   └── workflow_repo.py
│   ├── routers/
│   │   ├── actions.py
│   │   ├── events.py
│   │   ├── health.py
│   │   ├── runs.py
│   │   └── workflows.py
│   ├── cli.py
│   ├── config.py
│   ├── database.py
│   └── main.py
├── tests/
│   ├── conftest.py
│   ├── test_actions.py
│   ├── test_api_events.py
│   ├── test_api_runs.py
│   ├── test_api_workflows.py
│   ├── test_cli.py
│   ├── test_conditions.py
│   ├── test_executor.py
│   ├── test_scheduler.py
│   └── test_templating.py
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Getting Started

### 1. Setup Environment

```bash
uv venv .venv
.\.venv\Scripts\activate
uv pip install -e .
```

### 2. Run Test Suite

```bash
pytest -v
```

### 3. Initialize Sample Automations

```bash
autoflow init-sample
```

### 4. Inspect Available Workflows and Actions

```bash
autoflow workflow list
autoflow actions
```

### 5. Emit Events

```bash
autoflow event emit order.created --payload '{"order_id": 8841, "customer_name": "Marcus", "amount": 120, "email": "marcus@domain.org"}'
```

### 6. View Execution Logs

```bash
autoflow run list
autoflow stats
```

### 7. Run REST API Server

```bash
autoflow server --host 127.0.0.1 --port 8000
```

Access interactive Swagger documentation at `http://127.0.0.1:8000/docs`.

---

## REST API Specification

| Endpoint | Method | Description |
|---|---|---|
| `/health` | `GET` | System health check and status |
| `/api/v1/stats` | `GET` | Platform execution and workflow metrics |
| `/api/v1/actions` | `GET` | Action catalog and parameter schemas |
| `/api/v1/workflows` | `POST` | Create a new workflow definition |
| `/api/v1/workflows` | `GET` | List all workflows with run counts |
| `/api/v1/workflows/{id}` | `GET` | Retrieve workflow detail with steps |
| `/api/v1/workflows/{id}` | `PUT` | Update workflow definition |
| `/api/v1/workflows/{id}` | `DELETE` | Delete workflow |
| `/api/v1/workflows/{id}/toggle` | `POST` | Enable or disable workflow |
| `/api/v1/workflows/{id}/run` | `POST` | Dispatch manual workflow run |
| `/api/v1/events` | `POST` | Ingest external event and trigger matching automations |
| `/api/v1/events` | `GET` | List event audit logs |
| `/api/v1/runs` | `GET` | List workflow execution history |
| `/api/v1/runs/{id}` | `GET` | Retrieve run details and step logs |
| `/api/v1/runs/{id}/cancel` | `POST` | Cancel active execution |
