# Day 05 — Universal API CLI

A reusable, high-performance CLI tool and desktop application for sending REST requests, filtering JSON responses with JMESPath, formatting output (colorized syntax-highlighted JSON, rich tables, headers), managing named environment profiles and variables, tracking request history with instant replay, running multi-request latency benchmarks, and exporting data to JSON, CSV, and Markdown.

**Date:** Sep 16, 2026  
**Status:** ✅ Completed  

---

## Features

- **Universal REST Client**:
  - Full HTTP method support: `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `HEAD`.
  - Shorthand commands (`api get`, `api post`, `api put`, `api patch`, `api delete`) and generic dispatcher (`api req`).
  - Custom headers with `-H "Key: Value"` and query parameters with `-q "key=value"`.
  - Inline raw body string with `-d` or file loading with `-f filepath.json`.
  - Configurable timeouts and SSL verification flags.

- **JMESPath Filtering & Column Projection**:
  - Full JMESPath query engine (`--filter "items[?active].id"` or `--filter "users[*].name"`).
  - Column / field selection (`--fields "id,title,status"`) for selective viewing and exporting.

- **Rich Terminal Formatting**:
  - Syntax-highlighted, color-coded JSON responses.
  - Formatted terminal tables (`--format table`) with auto-detected columns for list responses and key-value pairs for object dictionaries.
  - Status code pills with intuitive color badges (2xx green, 3xx yellow, 4xx/5xx red), latency timing, payload size, and content-type.
  - Verbose mode (`-v`) revealing complete request/response wire details.

- **Data Export**:
  - Export response bodies and filtered slices directly into files with `--export filename.ext`.
  - Supported export formats: JSON (`.json`), flattened CSV (`.csv`), GitHub-Flavored Markdown table (`.md`), and raw text (`.txt`).

- **Environments & Dynamic Variables**:
  - Store reusable base URLs, default headers, and token variables per environment (`dev`, `staging`, `prod`).
  - Automatic template variable substitution using `{{variable_name}}` across URLs, headers, query parameters, and request bodies.
  - Switch active environments on the fly (`api env use <name>`).

- **Saved Request Collections**:
  - Save repetitive API calls with preconfigured headers, query parameters, method, and body.
  - Execute saved requests instantly with `api saved run <name>`.

- **Persistent Request History & Replay**:
  - Automatically records executed requests, status codes, latency, timestamps, and payload data in an isolated SQLite database.
  - Inspect history records (`api history list`, `api history show <id>`).
  - Instant replay of past requests with `api history replay <id>`.

- **Asynchronous Load & Latency Benchmarker**:
  - Benchmark any endpoint with configurable request counts and concurrency (`api bench <url> -n 20 -c 4`).
  - Computes comprehensive latency statistics: min, mean/avg, median (p50), p95, p99, max, throughput (req/s), and status code distributions.

- **Modern Desktop GUI (`api-gui` / `api-cli-gui`)**:
  - Pure-Python dark-mode GUI built with CustomTkinter.
  - HTTP method selector and endpoint address bar with dynamic variable support.
  - Request tabs for query parameters, headers, body, and collection saving.
  - Real-time response viewer with status badges, latency indicators, and payload size.
  - Live interactive JMESPath query filter bar with one-click reset.
  - One-click native file dialog exports to JSON, CSV, and Markdown.
  - Clickable history and saved collections sidebars.

---

## Installation & Setup

All dependencies and packaging are self-contained within this folder.

```powershell
cd 05-api-cli

python -m venv .venv

.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
pip install -e .
```

---

## CLI Command Reference

### 1. Sending Requests

```bash
# Simple GET request
api get https://jsonplaceholder.typicode.com/todos/1

# GET request with tabular output
api get https://jsonplaceholder.typicode.com/todos/1 --format table

# JMESPath filtering and field picking
api get https://jsonplaceholder.typicode.com/todos --filter "[0:5]" --fields "id,title,completed" --format table

# POST request with JSON body
api post https://httpbin.org/post -d '{"username":"ckzz","role":"admin"}'

# Exporting filtered response directly to CSV
api get https://jsonplaceholder.typicode.com/todos --filter "[0:10]" --export todos.csv

# View headers only
api get https://jsonplaceholder.typicode.com/todos/1 --format headers

# Verbose mode showing wire details
api get https://jsonplaceholder.typicode.com/todos/1 -v
```

### 2. Managing Environments & Variables

```bash
# Create an environment with base URL and variables
api env set staging --base-url https://api.staging.example.com -v api_token=sec_99182 -H "Authorization: Bearer {{api_token}}"

# List all configured environments
api env list

# Set active environment
api env use staging

# Check current active environment
api env current

# Request using variable interpolation
api get {{base_url}}/v1/users

# Clear active environment
api env use --clear
```

### 3. Saved Request Collections

```bash
# Save a request
api saved save list_todos https://jsonplaceholder.typicode.com/todos -X GET

# List saved requests
api saved list

# Run a saved request
api saved run list_todos --format table

# Delete a saved request
api saved delete list_todos
```

### 4. History & Replay

```bash
# View recent request history
api history list --limit 15

# Show complete details of a specific request
api history show 1

# Replay a past request
api history replay 1 --format table

# Clear history
api history clear
```

### 5. Running Latency Benchmarks

```bash
# Benchmark an endpoint with 20 requests and concurrency of 4
api bench https://jsonplaceholder.typicode.com/todos/1 -n 20 -c 4
```

### 6. Desktop GUI

```bash
# Launch the desktop application
api-gui
```

---

## Architecture & Design

```text
05-api-cli/
├── pyproject.toml              Packaging manifest and CLI entry points (api, api-cli, api-gui)
├── requirements.txt            Package dependencies (click, rich, httpx, jmespath, customtkinter, pytest)
├── README.md                   Project documentation and guides
├── .gitignore                  Isolated git ignore rules
├── api_cli/
│   ├── __init__.py             Package metadata
│   ├── config.py               Configuration defaults and database path resolver
│   ├── models.py               Typed dataclasses (RequestConfig, ResponseResult, Environment, SavedRequest, HistoryEntry, BenchmarkStats)
│   ├── db.py                   SQLite persistence for environments, settings, saved requests, and history
│   ├── client.py               HTTP client engine, variable interpolation ({{var}}), and request logger
│   ├── filter.py               JMESPath filtering engine and column projection
│   ├── formatter.py            Rich terminal formatters (JSON, Table, Headers, Summary badges, Verbose wire view)
│   ├── exporter.py             JSON, CSV (flattened), and Markdown report exporters
│   ├── benchmarker.py          Asynchronous multi-request latency benchmark engine
│   ├── cli.py                  Click & Rich command-line interface
│   └── gui.py                  CustomTkinter dark-mode desktop GUI application
└── tests/
    ├── __init__.py             Test package marker
    ├── test_filter.py          JMESPath filter and field projection tests
    ├── test_db.py              Database CRUD, environments, saved requests, and history tests
    ├── test_client.py          Client execution, variable interpolation, and timeout tests
    ├── test_exporter.py        Export formatters (JSON, CSV, Markdown) tests
    ├── test_benchmarker.py     Latency statistics and asynchronous benchmark tests
    ├── test_cli.py             Click CLI integration tests (commands, env, saved, history, bench)
    └── test_gui.py             GUI structure and parsing tests
```

---

## Running Tests

Run the full automated test suite using pytest:

```powershell
pytest -v
```
