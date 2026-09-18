# Day 07 — Price Tracker

A robust, production-grade product price tracker built with Python. Features multi-strategy web price and stock extraction (CSS selectors, Schema.org JSON-LD microdata, OpenGraph meta tags, and heuristic fallbacks), multi-currency numeric parsing, SQLite historical persistence, price drop and all-time low alert detection, pluggable notifications (terminal, webhook, log file), terminal ASCII sparklines and trend charts, structured exports (JSON, CSV, Markdown), a rich interactive CLI, and a modern CustomTkinter dark-mode desktop GUI.

**Date:** Sep 18, 2026  
**Status:** ✅ Completed  

---

## Features

- **Multi-Strategy Price & Stock Extraction**:
  - **Custom CSS Selectors**: Target exact price elements and data attributes.
  - **Schema.org JSON-LD**: Automatically inspects `<script type="application/ld+json">` for `Product` and `Offer` schema, extracting `price`, `priceCurrency`, and `availability`.
  - **OpenGraph & Meta Tags**: Inspects `product:price:amount`, `og:price:amount`, `product:price:currency`, and `itemprop="price"`.
  - **Heuristic Fallback Engine**: Common e-commerce selector patterns (`.price`, `.product-price`, `.price_color`, `.a-price-whole`, etc.).
  - **Universal Number & Currency Normalizer**: Parses varied currency formats (`$1,299.99`, `€ 89,90`, `£45.00`, `¥5,000`, `149.99 CAD`).
  - **Stock & Availability Detection**: Detects in-stock vs out-of-stock from schema availability URLs and keyword markers.

- **Persistent Historical Database (SQLite)**:
  - Tracks products, timestamped price records, and price alert histories.
  - Computes statistical metrics: current price, lowest price (all-time low), highest price, average price, net price change percentage.

- **Intelligent Price Alerts & Notifications**:
  - **Target Reached**: Triggers when a product reaches or drops below user-specified target.
  - **All-Time Low**: Triggers when the price drops below all previously recorded historical lows.
  - **Percentage Drop**: Triggers on meaningful price drops exceeding configurable threshold (e.g. >= 5%).
  - **Back in Stock**: Alerts when an out-of-stock product becomes available again.
  - **Pluggable Notifiers**: Terminal colored banners, Discord/Slack webhooks, and append-only log files.

- **Terminal Visualizations**:
  - Unicode sparklines (` ▂▃▅▆▇█`) rendered directly inside product list tables.
  - ASCII historical price trend charts with min/max scale and date tracking.
  - Price change indicators with percentage changes and colored arrows (`▼ -15.2%`, `▲ +5.0%`).

- **Structured Data Export & Import**:
  - Export tracked products and historical records to **JSON**, **CSV**, and **Markdown** reports.
  - Bulk import product watchlists from JSON or CSV files.

- **Interactive Rich CLI**:
  - Fast commands: `add`, `list`, `check`, `history`, `alerts`, `stats`, `delete`, `export`, `import-file`, and `watch` (continuous monitoring daemon).

- **Modern CustomTkinter Desktop GUI**:
  - Clean dark-mode dashboard with real-time statistics cards.
  - Products manager with stock badges, live price updates, and add/delete actions.
  - Interactive history viewer with ASCII trend charts and tabular logs.
  - Live alerts feed and one-click data exporter.

---

## Architecture

```text
07-price-tracker/
├── .gitignore
├── pyproject.toml
├── requirements.txt
├── README.md
├── price_tracker/
│   ├── __init__.py           # Package exports
│   ├── config.py             # Default paths, timeouts, currency mappings
│   ├── models.py             # Product, PriceRecord, PriceAlert, ScrapeResult
│   ├── extractor.py          # Multi-strategy HTML price & stock extractor
│   ├── scraper.py            # Resilient HTTP client
│   ├── db.py                 # SQLite database manager & stats
│   ├── notifier.py           # Console, Webhook, and File alert dispatchers
│   ├── tracker.py            # Tracking coordinator & change detection
│   ├── chart.py              # Sparklines & ASCII trend charts
│   ├── exporter.py           # JSON, CSV, Markdown exporters & importers
│   ├── cli.py                # Click and Rich terminal CLI
│   └── gui.py                # CustomTkinter modern desktop GUI
└── tests/
    ├── __init__.py
    ├── test_extractor.py     # HTML parsers, JSON-LD, meta, heuristics
    ├── test_db.py            # SQLite schema, CRUD, stats, alerts
    ├── test_tracker.py       # Tracking engine, price drops, alerts
    ├── test_notifier.py      # Notifier channels & payloads
    ├── test_chart.py         # Sparkline and ASCII chart rendering
    ├── test_exporter.py      # Export & import validations
    ├── test_cli.py           # CLI commands & outputs
    └── test_gui.py           # Desktop GUI initialization
```

---

## Installation & Setup

1. Navigate to the project directory:
   ```bash
   cd 07-price-tracker
   ```

2. Activate the virtual environment:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

3. (Optional) Reinstall dependencies or editable package if needed:
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

---

## CLI Usage Guide

### 1. Add a Product to Track
```bash
price-tracker add "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html" --name "A Light in the Attic" --target-price 50.00 --tag "Books"
```
Optional flags:
- `--selector`, `-s`: Custom CSS selector for target price.
- `--target-price`, `-t`: Target price threshold for alerts.
- `--currency`, `-c`: Currency code (USD, EUR, GBP, JPY, CAD, etc.).
- `--tag`: Categorization tag.

### 2. List All Tracked Products
```bash
price-tracker list
```
Displays a table with ID, Product Name, Current Price, Lowest Price, Target Price, Stock status, Category Tag, and an inline sparkline trend.

Filter by tag or stock:
```bash
price-tracker list --tag "Books"
price-tracker list --in-stock
```

### 3. Check Prices on Demand
Check a single product by ID:
```bash
price-tracker check 1
```

Check all tracked products:
```bash
price-tracker check
```

### 4. View Price History and ASCII Chart
```bash
price-tracker history 1
```
Displays timestamped price snapshots, percentage changes, and a terminal trend chart.

### 5. Product Statistics Summary
```bash
price-tracker stats 1
```
Displays current price, target price, all-time lowest, highest, historical average, and net change percentage.

### 6. View & Manage Triggered Alerts
```bash
price-tracker alerts
price-tracker alerts --product-id 1
price-tracker alerts --clear
```

### 7. Export Data
Export tracked products and history to JSON, CSV, or Markdown:
```bash
price-tracker export --format json
price-tracker export --format csv
price-tracker export --format md
```

### 8. Bulk Import Products
```bash
price-tracker import-file products.json
price-tracker import-file products.csv
```

### 9. Continuous Watcher (Daemon Mode)
Continuously monitor products with an interval (default: 3600s):
```bash
price-tracker watch --interval 300
```

---

## Desktop GUI

Launch the desktop interface:
```bash
price-tracker-gui
```
or:
```bash
python -m price_tracker.gui
```

### GUI Features:
- **Products Tab**: View all items, stock status badges, prices, single or batch check, and add new items with live selector testing.
- **History & Stats Tab**: Select any item to view high-level metric cards (Current, Low, Target, Change) and a chronological price log.
- **Alerts Feed**: Review all triggered price drop and target-reached alerts.
- **Export Tab**: One-click exports to JSON, CSV, or Markdown.

---

## Running Tests

Run the test suite:
```powershell
cd 07-price-tracker
.\.venv\Scripts\pytest -v
```
All 30 unit and integration tests verify extraction rules, database integrity, alert triggering, exporters, CLI runner, and GUI initialization.
