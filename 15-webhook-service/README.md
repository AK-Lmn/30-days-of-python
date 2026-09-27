# Day 15 — HookRelay: Webhook Ingestion & Delivery Service

A high-performance, fault-tolerant webhook gateway and delivery service built with Python 3.13, FastAPI, SQLAlchemy 2.0 (asyncio), and Click. HookRelay ingests webhook events from external providers (Stripe, GitHub, custom services), verifies cryptographic signatures, guarantees idempotent processing, routes events to subscribers using pattern matching, signs outbound payloads, and delivers them with exponential backoff and dead-letter queue (DLQ) support.

**Date:** Sep 26, 2026  
**Status:** ✅ Complete  

---

## Architecture Overview

```
                               Incoming Webhooks
                  [Stripe]          [GitHub]          [Custom]
                     │                 │                 │
                     ▼                 ▼                 ▼
          ┌────────────────────────────────────────────────────────┐
          │               HookRelay Ingress Gateway                │
          │                                                        │
          │  1. Cryptographic Verification (HMAC, Stripe, GitHub)   │
          │  2. Deduplication & Idempotency Key Validation         │
          │  3. Event Type Extraction & Payload Storage            │
          │  4. Fast Async 202 Acceptance / Acknowledgment         │
          └───────────────────────────┬────────────────────────────┘
                                      │
                                      ▼
          ┌────────────────────────────────────────────────────────┐
          │             Event Routing & Fanout Engine              │
          │                                                        │
          │  • Matches event types against subscription patterns   │
          │    (e.g., "order.*", "payment.succeeded", "*")         │
          │  • Creates persistent Delivery & DeliveryAttempt rows  │
          └───────────────────────────┬────────────────────────────┘
                                      │
                                      ▼
          ┌────────────────────────────────────────────────────────┐
          │              Outbound Delivery & Retries               │
          │                                                        │
          │  • Outbound payload signing (HMAC-SHA256 timestamp)    │
          │  • Async HTTP POST to destination targets              │
          │  • Exponential backoff for server errors (5xx/timeouts)│
          │  • Non-retryable client errors (4xx)                   │
          │  • Dead Letter Queue (DLQ) upon retry exhaustion       │
          │  • Manual replay API & CLI trigger                     │
          └────────────────────────────────────────────────────────┘
```

---

## Key Features

1. **Multi-Strategy Cryptographic Verification**
   - **Stripe**: Parses `t=<timestamp>,v1=<signature>` header, protects against replay attacks with configurable tolerance windows, and verifies HMAC-SHA256 signature against `{timestamp}.{raw_body}`.
   - **GitHub**: Validates `X-Hub-Signature-256: sha256=<hex>` against incoming raw body.
   - **HMAC-SHA256**: Standard HMAC hex digest validation from headers (`X-Signature`, `X-Webhook-Signature`, etc.).
   - **Shared Token**: Header token authentication (`Bearer` or direct token match).
   - **None**: For development and internal environments.

2. **Idempotency & Deduplication**
   - Extracts unique event identifiers from headers (`Idempotency-Key`, `X-GitHub-Delivery`) or payload bodies (`id`, `idempotency_key`).
   - Automatically detects duplicate deliveries and responds with HTTP 200 and existing event metadata without re-executing duplicate webhook flows.

3. **Pattern-Based Subscription Routing**
   - Fanout delivery to multiple destination webhooks.
   - Wildcard glob pattern matching (e.g., `payment.*`, `order.*`, or catch-all `*`).
   - Per-subscription configurations: destination URL, signing secret, retry limits, backoff base, and timeouts.

4. **Outbound Payload Signing**
   - Downstream subscribers receive verified webhooks with signing headers:
     - `X-HookRelay-Signature`: `t=<timestamp>,v1=<hmac_sha256>`
     - `X-HookRelay-Timestamp`: UNIX timestamp of outbound dispatch
     - `X-HookRelay-Event-Id`: Unique event ID
     - `X-HookRelay-Delivery-Id`: Unique delivery attempt ID

5. **Fault-Tolerant Delivery & Dead Letter Queue (DLQ)**
   - Tracks every delivery attempt with HTTP status codes, latency duration in milliseconds, request/response headers, response body preview, and error messages.
   - Intelligent retry logic:
     - Transient server errors (5xx) and connection timeouts enter exponential backoff retry scheduling:
       $$\text{delay} = \text{backoff\_base} \times 2^{\text{attempt} - 1}$$
     - Client errors (4xx) are marked as non-retryable failures.
     - Exhausted attempts transition the delivery to `dlq` (Dead Letter Queue).
   - On-demand replay functionality via REST API and CLI to re-dispatch failed or DLQ deliveries.

6. **FastAPI REST Service & Rich CLI**
   - Complete asynchronous REST API with OpenAPI documentation at `/docs`.
   - Rich interactive CLI with formatted tables, execution details, simulation tool, and server runners.

---

## Directory Layout

```text
15-webhook-service/
├── hookrelay/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── deliveries.py
│   │   │   ├── endpoints.py
│   │   │   ├── events.py
│   │   │   ├── ingest.py
│   │   │   └── subscriptions.py
│   │   ├── app.py
│   │   └── deps.py
│   ├── models/
│   │   ├── delivery.py
│   │   ├── endpoint.py
│   │   ├── event.py
│   │   └── subscription.py
│   ├── schemas/
│   │   ├── delivery.py
│   │   ├── endpoint.py
│   │   ├── event.py
│   │   └── subscription.py
│   ├── security/
│   │   ├── signer.py
│   │   └── verifier.py
│   ├── services/
│   │   ├── delivery_service.py
│   │   ├── endpoint_service.py
│   │   ├── event_service.py
│   │   └── subscription_service.py
│   ├── cli.py
│   ├── config.py
│   └── database.py
├── tests/
│   ├── conftest.py
│   ├── test_api.py
│   ├── test_cli.py
│   ├── test_delivery_and_retries.py
│   ├── test_ingest.py
│   ├── test_routing.py
│   └── test_signatures.py
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Installation & Setup

1. **Activate Virtual Environment:**
   ```bash
   cd 15-webhook-service
   .\.venv\Scripts\activate
   ```

2. **Install Dependencies in Editable Mode:**
   ```bash
   pip install -e .
   ```

---

## CLI Usage

### 1. Manage Ingestion Endpoints
```bash
# Create an endpoint with Stripe signature verification
hookrelay endpoint create stripe-in "Stripe Production" --strategy stripe --secret whsec_sample

# Create an endpoint with GitHub signature verification
hookrelay endpoint create github-in "GitHub Push" --strategy github --secret sample_secret

# List all endpoints
hookrelay endpoint list
```

### 2. Manage Destination Subscriptions
```bash
# Forward order events to an internal accounting microservice
hookrelay subscription create "Accounting Service" http://localhost:9000/hooks --pattern "order.*" --retries 3

# Forward all events to a data lake
hookrelay subscription create "Data Lake" http://localhost:9100/lake --pattern "*"

# List subscriptions
hookrelay subscription list
```

### 3. Simulate Incoming Webhooks
```bash
# Test ingestion and automatic signature generation
hookrelay simulate stripe-in --type order.created --payload '{"order_id": 4821, "amount": 120.00}'
```

### 4. Inspect Deliveries & Replay Failures
```bash
# List all deliveries and their status (success, pending, dlq, failed)
hookrelay delivery list

# Replay any delivery attempt manually
hookrelay delivery replay <delivery_id>

# Process pending retry deliveries whose scheduled backoff has elapsed
hookrelay delivery process-retries
```

### 5. Launch REST API Server
```bash
hookrelay serve --host 127.0.0.1 --port 8000
```

---

## REST API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/ingest/{slug}` | Ingest and authenticate external webhook |
| `POST` | `/api/v1/endpoints` | Register a new webhook ingress endpoint |
| `GET` | `/api/v1/endpoints` | List configured endpoints |
| `GET` | `/api/v1/endpoints/{id}` | Retrieve endpoint configuration |
| `PATCH` | `/api/v1/endpoints/{id}` | Update endpoint configuration |
| `DELETE` | `/api/v1/endpoints/{id}` | Delete endpoint |
| `POST` | `/api/v1/subscriptions` | Register new destination subscription |
| `GET` | `/api/v1/subscriptions` | List subscriptions |
| `GET` | `/api/v1/subscriptions/{id}` | Retrieve subscription details |
| `PATCH` | `/api/v1/subscriptions/{id}` | Update subscription |
| `DELETE` | `/api/v1/subscriptions/{id}` | Delete subscription |
| `GET` | `/api/v1/events` | List ingested events (filtered by endpoint, type, status) |
| `GET` | `/api/v1/events/{id}` | View event payload, headers, and raw body |
| `GET` | `/api/v1/events/{id}/deliveries` | List all deliveries triggered by an event |
| `GET` | `/api/v1/deliveries` | List deliveries (filtered by status, event, sub) |
| `GET` | `/api/v1/deliveries/{id}` | View delivery details and execution attempts |
| `POST` | `/api/v1/deliveries/{id}/replay` | Manually re-trigger delivery attempt |
| `POST` | `/api/v1/deliveries/process-retries`| Process due pending retries |
| `GET` | `/health` | Service health check |

---

## Running the Test Suite

Run the full async test suite covering signatures, replay attacks, duplicate detection, routing, delivery backoff, DLQ, API, and CLI:

```bash
.\.venv\Scripts\pytest -v
```
