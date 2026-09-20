# Day 09 — API Aggregator

A high-performance, asynchronous API aggregation service built with Python. Combines data from multiple disparate external APIs (HackerNews, GitHub Events, Dev.to, CoinGecko, Coinbase, Binance, Open-Meteo, wttr.in, and custom endpoints) into a single, standardized envelope schema with cross-provider data reconciliation, circuit breakers, asynchronous rate limiting, in-memory TTL caching, a FastAPI REST service, an interactive Rich CLI, and a modern CustomTkinter desktop GUI.

**Date:** Sep 20, 2026  
**Status:** ✅ Completed

---

## Features

- **Multi-Domain Aggregation**:
  - **Tech & Developer News**: Aggregates and deduplicates top stories from HackerNews (Firebase API), GitHub Trending/Repositories (GitHub REST API), and Dev.to articles.
  - **Cryptocurrency Exchange Rates**: Concurrently queries CoinGecko, Coinbase, and Binance, calculating volume-weighted and average spot rates, min/max spreads, and cross-exchange discrepancy percentages.
  - **Weather & Geocoding**: Normalizes current weather conditions, coordinates, temperatures (°C / °F), humidity, and wind speeds from Open-Meteo and wttr.in.
  - **Executive Overview**: Concurrently generates a unified cross-domain snapshot combining tech headlines, cryptocurrency prices, and local weather.
  - **Dynamic Custom Fanout**: Accepts arbitrary lists of HTTP endpoints, issuing parallel requests and compiling response statuses, latencies, and payload data.

- **Standardized Response Envelope**:
  - Every endpoint and CLI query produces a consistent schema:
    ```json
    {
      "status": "SUCCESS",
      "timestamp": "2026-09-20T08:57:47.874032+00:00",
      "latency_ms": 2449.4,
      "sources_queried": ["hackernews", "github", "devto"],
      "sources_succeeded": ["hackernews", "github", "devto"],
      "sources_failed": [],
      "cached": false,
      "count": 5,
      "data": [...]
    }
    ```

- **Resilience & Fault Tolerance**:
  - **Circuit Breaker Pattern**: Per-provider state machine (`CLOSED` → `OPEN` → `HALF_OPEN`) preventing cascading latency spikes when third-party APIs fail.
  - **Asynchronous Token Bucket Rate Limiter**: Smooths out burst queries to prevent hitting upstream rate limits.
  - **Exponential Backoff & Retries**: Retries failed network requests with jitter.
  - **Graceful Degradation**: Supports partial results (`status: "PARTIAL"`) and deterministic mock fallbacks when offline or encountering rate limits.

- **In-Memory TTL Cache**:
  - Async-safe LRU cache with configurable expiration per domain.
  - Tracks hit count, miss count, evictions, and real-time hit ratio telemetry.
  - Supports cache bypassing (`--no-cache`) and programmatic cache clearing (`DELETE /api/v1/cache`).

- **FastAPI REST API**:
  - Auto-generated OpenAPI / Swagger UI at `/docs`.
  - Comprehensive endpoints:
    - `GET /` — API metadata and available routes
    - `GET /health` — Provider health and circuit statuses
    - `GET /metrics` — Aggregation latency, hit ratio, and provider statistics
    - `GET /api/v1/aggregate/news` — Aggregated tech news
    - `GET /api/v1/aggregate/crypto` — Reconciled cryptocurrency rates
    - `GET /api/v1/aggregate/weather` — Normalized weather report
    - `GET /api/v1/aggregate/overview` — Multi-domain summary
    - `POST /api/v1/aggregate/custom` — Ad-hoc multi-URL fanout
    - `DELETE /api/v1/cache` — Clear in-memory cache

- **Rich Interactive CLI**:
  - `serve`: Launch Uvicorn REST server.
  - `news`: Fetch and display unified tech news in a Rich table.
  - `crypto`: Fetch and display reconciled crypto rates with cross-exchange spread.
  - `weather`: Fetch and display normalized weather panel.
  - `overview`: Fetch and display an executive overview.
  - `status`: Display health, circuit states, and cache telemetry.
  - `benchmark`: Benchmark parallel async aggregation vs sequential fanout.
  - `export`: Export aggregated data to JSON or CSV.
  - `gui`: Launch the CustomTkinter desktop GUI.

- **Modern CustomTkinter GUI**:
  - Dark-mode desktop application with sidebar domain navigation.
  - Live query controls, latency indicators, and interactive JSON/tabular results viewer.

---

## Architecture

```text
09-api-aggregator/
├── .gitignore
├── pyproject.toml
├── requirements.txt
├── README.md
├── api_aggregator/
│   ├── __init__.py               # Public package exports
│   ├── config.py                 # App configuration & defaults
│   ├── models.py                 # Pydantic schemas & UnifiedEnvelope
│   ├── circuit_breaker.py        # Circuit breaker state machine
│   ├── rate_limiter.py           # Async token bucket rate limiter
│   ├── cache.py                  # In-memory async TTL LRU cache
│   ├── client.py                 # Resilient HTTP client with retries
│   ├── providers/
│   │   ├── __init__.py           # Providers export
│   │   ├── base.py               # BaseProvider contract
│   │   ├── news.py               # HackerNews, GitHub, Dev.to
│   │   ├── crypto.py             # CoinGecko, Coinbase, Binance
│   │   ├── weather.py            # Open-Meteo, wttr.in
│   │   └── custom.py             # Generic multi-URL fanout
│   ├── engine.py                 # AggregationEngine orchestrator
│   ├── server.py                 # FastAPI application
│   ├── cli.py                    # Rich CLI commands
│   └── gui.py                    # CustomTkinter desktop GUI
└── tests/
    ├── __init__.py
    ├── test_models.py            # Model serialization & schemas
    ├── test_circuit_breaker.py   # Circuit transitions & recovery
    ├── test_rate_limiter.py      # Token replenishment & throttling
    ├── test_cache.py             # TTL expiration & LRU eviction
    ├── test_providers.py         # Provider parsers & fallback modes
    ├── test_engine.py            # Engine concurrency & reconciliation
    ├── test_server.py            # FastAPI endpoints & status codes
    ├── test_cli.py               # Click CLI runner tests
    └── test_gui.py               # Desktop GUI initialization
```

---

## Installation & Setup

1. Navigate to the project directory:
   ```bash
   cd 09-api-aggregator
   ```

2. Create and activate a virtual environment:
   ```powershell
   uv venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies in editable mode:
   ```powershell
   uv pip install -e ".[dev]"
   ```

---

## CLI Usage

### Fetch Aggregated Tech News
```bash
api-aggregator news --limit 5
```
Options:
- `--limit <int>`: Number of headlines to display (default: 5).
- `--no-cache`: Force live fetch bypassing cache.
- `--mock`: Force deterministic mock data.

### Fetch Reconciled Cryptocurrency Rates
```bash
api-aggregator crypto --coins BTC,ETH,SOL
```
Displays average USD prices across CoinGecko, Coinbase, and Binance, along with 24h change percentages and cross-exchange price spreads.

### Fetch Weather Report
```bash
api-aggregator weather --city "Tokyo"
```

### Fetch Executive Overview
```bash
api-aggregator overview
```

### Check Provider Health & Cache Telemetry
```bash
api-aggregator status
```

### Benchmark Concurrency Speedup
```bash
api-aggregator benchmark --iterations 3
```

### Export Aggregated Data
```bash
api-aggregator export --domain news --format json --output exports/news.json
api-aggregator export --domain crypto --format csv --output exports/crypto.csv
```

### Launch Desktop GUI
```bash
api-aggregator gui
```

---

## REST API Server

Start the API server:
```bash
api-aggregator serve --port 8000
```
Interactive OpenAPI documentation is available at:
`http://127.0.0.1:8000/docs`

### Sample Requests

#### Aggregated News:
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/aggregate/news?limit=5"
```

#### Reconciled Crypto:
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/aggregate/crypto?symbols=BTC,ETH,SOL"
```

#### Weather:
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/aggregate/weather?city=Berlin"
```

#### Multi-Domain Overview:
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/aggregate/overview"
```

#### Custom Dynamic Fanout:
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/aggregate/custom" \
     -H "Content-Type: application/json" \
     -d '{"urls": ["https://httpbin.org/get", "https://api.github.com/zen"]}'
```

#### Purge Cache:
```bash
curl -X DELETE "http://127.0.0.1:8000/api/v1/cache"
```

---

## Testing

Run all unit and integration tests with pytest:
```powershell
.\.venv\Scripts\pytest -v
```

All 56 tests execute in under 2 seconds with 100% pass rate.
