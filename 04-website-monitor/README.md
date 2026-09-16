# Day 04 — Website Monitor

A high-performance CLI tool and desktop application for monitoring website and API endpoint uptime, latency, status codes, keyword content assertions, and SSL certificate expiration. Features SQLite persistence, automated incident tracking, multi-channel webhook notifications, real-time terminal dashboards, and a CustomTkinter GUI.

**Date:** Sep 15, 2026  
**Status:** ✅ Completed  

---

## Features

- **Endpoint Health & Uptime Tracking**:
  - Validates HTTP response codes against expected status or ranges.
  - Accurate high-resolution latency measurement (in milliseconds).
  - Response body keyword verification to guard against soft 200 errors.
  - Automatic SSL certificate expiry inspection and warning alerts.
  - Supports custom HTTP methods (GET, POST, HEAD, PUT, DELETE) and custom headers.
- **Incident & Outage Lifecycle Management**:
  - Automatically detects outages based on consecutive failure thresholds to avoid flapping.
  - Opens incidents with failure reason and exact outage start timestamps.
  - Automatically resolves incidents upon service recovery and calculates total downtime.
- **Rich Terminal CLI (`web-monitor`)**:
  - `web-monitor target add <url>`: Add new monitor targets with methods, expected status, keywords, and tags.
  - `web-monitor target list`: Display all configured targets in formatted tables.
  - `web-monitor target remove <id>`: Delete targets and associated history.
  - `web-monitor check [id|url]`: Perform on-demand checks on single or all active targets.
  - `web-monitor stats [id]`: View uptime percentage, min/avg/p95/max latency, and SLA compliance.
  - `web-monitor watch`: Stream continuous real-time health checks to the terminal.
  - `web-monitor dashboard`: Live terminal dashboard with auto-refreshing KPI metrics and activity feeds.
  - `web-monitor incidents`: Review active outages and historical downtime.
  - `web-monitor export`: Export reports in Markdown, JSON, or CSV.
  - `web-monitor prune`: Clean up old check logs based on configurable retention days.
- **Modern Pure-Python Desktop GUI (`web-monitor-gui`)**:
  - Built with CustomTkinter in a dark-mode theme.
  - Overview KPI cards for Total Monitored, Overall Uptime, Active Outages, and Avg Latency.
  - Live Endpoint Status table with real-time response times and uptime badges.
  - Interactive Target Manager for adding and deleting endpoints.
  - Outage and incident log viewer with duration tracking.
  - Asynchronous background monitoring worker toggle.
  - One-click native file dialog export to Markdown, JSON, and CSV.
- **Alerting & Notifications**:
  - Multi-platform webhook dispatcher for Slack, Discord, and generic JSON webhooks.
  - Automated state transition alerts (OUTAGE, RECOVERY, SSL_EXPIRING).

---

## Installation & Setup

All dependencies and packaging are self-contained within this folder.

```powershell
cd 04-website-monitor

python -m venv .venv

.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
pip install -e .
```

---

## CLI Command Reference

### 1. Managing Monitor Targets

```bash
web-monitor target add https://api.github.com --name "GitHub API" --tag production
web-monitor target add https://httpbin.org/status/200 --name "HTTPBin Status" --expected-status 200
web-monitor target add https://example.com --keyword "Example Domain" --timeout 5.0

web-monitor target list
web-monitor target list --tag production

web-monitor target remove 1
```

### 2. Running Health Checks

```bash
web-monitor check
web-monitor check 1
web-monitor check https://api.github.com
```

### 3. Viewing Stats & SLA Metrics

```bash
web-monitor stats
web-monitor stats 1 --hours 24
```

### 4. Continuous Watch & Live Dashboard

```bash
web-monitor watch --interval 30
web-monitor dashboard --interval 5
```

### 5. Reviewing Incidents

```bash
web-monitor incidents
web-monitor incidents --unresolved
```

### 6. Exporting Reports

```bash
web-monitor export --format md --output uptime_report.md
web-monitor export --format json --output uptime_report.json
web-monitor export --format csv --output uptime_report.csv
```

### 7. Launching Desktop GUI

```bash
web-monitor gui
web-monitor-gui
```

---

## Architecture & Design

```
04-website-monitor/
├── pyproject.toml              Packaging manifest and CLI entry points
├── requirements.txt            Package dependency list
├── README.md                   Project documentation
├── .gitignore                  Isolated git ignore rules
├── website_monitor/
│   ├── __init__.py             Package metadata
│   ├── config.py               Configuration defaults and database paths
│   ├── models.py               Typed dataclasses (MonitorTarget, CheckResult, Incident, TargetStats)
│   ├── db.py                   SQLite persistence, CRUD, aggregate queries, and log pruning
│   ├── checker.py              HTTP latency and SSL certificate validation engine
│   ├── notifier.py             Webhook dispatcher and state-transition manager
│   ├── engine.py               Concurrent check scheduler and incident tracker
│   ├── exporter.py             JSON, CSV, and Markdown report formatters
│   ├── cli.py                  Click & Rich command-line interface
│   └── gui.py                  CustomTkinter dark-mode desktop GUI application
└── tests/
    ├── __init__.py             Test package marker
    ├── test_models.py          Model validation and serialization tests
    ├── test_db.py              Database CRUD, incidents, and query tests
    ├── test_checker.py         HTTP requests, SSL, and error handling tests
    ├── test_engine.py          Engine scheduler and incident transition tests
    ├── test_notifier.py        Webhook formatters and alert tests
    ├── test_exporter.py        Report generation tests
    └── test_cli.py             Click CLI integration tests
```

---

## Running Tests

Run the full automated test suite using pytest:

```powershell
pytest -v
```
