# Day 06 — Web Scraper Engine

A reusable, high-performance web scraping engine and desktop application built with Python. Features declarative CSS/attribute extraction, pagination strategies (next link, query parameter, offset), polite domain rate limiting with jitter, exponential backoff retries, robots.txt compliance, SHA-256 disk caching, structured data exports (JSON, CSV, JSONL, Markdown, SQLite), an interactive CLI, and a modern CustomTkinter dark-mode GUI.

**Date:** Sep 17, 2026  
**Status:** ✅ Completed  

---

## Features

- **Robust HTTP Core & Resilience**:
  - Built on `httpx` with timeout management and automatic redirect following.
  - Exponential backoff retry system with jitter for transient errors (`429`, `500`, `502`, `503`, `504`) and connection drops.
  - User-agent rotation, custom request headers, and cookie handling.

- **Polite Crawling & Compliance**:
  - **Per-Domain Rate Limiting**: Enforces minimum request intervals per host with randomized jitter to prevent rate limit blocks.
  - **Robots.txt Enforcement**: Automatic fetch and compliance verification against target `robots.txt` rules and crawl delay directives.

- **Response Caching Layer**:
  - SHA-256 URL-hashed disk cache with configurable Time-To-Live (TTL).
  - Accelerates development, testing, and debugging while reducing traffic on target servers.

- **Declarative Parser Engine**:
  - BeautifulSoup (`html.parser`) based selector engine.
  - Flexible item rules defining target CSS selectors, extraction targets (`text`, `html`, `href`, `src`, custom element attributes), regex pattern groups, type casting (`str`, `int`, `float`, `bool`, `list`), and default fallbacks.
  - Supports both repeating collections (container selector) and single-page record extraction.
  - Live selector testing utility to quickly verify CSS queries against any webpage.

- **Configurable Pagination**:
  - **Next Link**: Follows pagination links (`<a rel="next">`, `li.next > a`) and resolves relative URLs.
  - **Page Number Parameter**: Automatically increments query parameters (`?page=1`, `?page=2`).
  - **Offset & Limit**: Advances offset counters (`?offset=0&limit=20`, `?offset=20&limit=20`).
  - Safeguards against duplicate URL loops, maximum page ceilings, and total item quotas.

- **Structured Data Exporting**:
  - Export scraped datasets into 5 formats:
    - **JSON** (indented, UTF-8)
    - **JSON Lines / NDJSON** (`.jsonl`)
    - **CSV** (auto-detected headers, escaped fields)
    - **Markdown** (GitHub-Flavored Markdown tables)
    - **SQLite** (creates table and inserts structured records)

- **Scraping Presets**:
  - Pre-configured templates for common targets (`quotes`, `books`, `hackernews`, `products`).

- **Rich Terminal CLI**:
  - Colorized status tables, live progress bars, item previews, selector inspector, and cache management commands.

- **Modern Desktop GUI**:
  - Dark-mode interface built with CustomTkinter.
  - Visual field rule builder, preset loader, selector tester tab, live table preview, raw JSON inspector, and one-click file dialog exports.

---

## Architecture

```text
06-web-scraper/
├── .gitignore
├── pyproject.toml
├── requirements.txt
├── README.md
├── web_scraper/
│   ├── __init__.py           # Package exports
│   ├── config.py             # Default configurations, paths, user agents
│   ├── models.py             # ItemRule, PaginationConfig, ScrapeJob, ScrapeResult
│   ├── client.py             # Resilient HTTP client with backoff & retry
│   ├── rate_limiter.py       # Per-domain rate limiter with random jitter
│   ├── robots.py             # Robots.txt fetcher and validator
│   ├── cache.py              # SHA-256 disk response cache
│   ├── parser.py             # BeautifulSoup extractor with typing & regex
│   ├── pagination.py         # Next-link, page-param, and offset traversers
│   ├── engine.py             # Scraper pipeline coordinator
│   ├── exporter.py           # JSON, CSV, JSONL, Markdown, SQLite exporters
│   ├── presets.py            # Built-in scraper presets
│   ├── cli.py                # Click and Rich command-line interface
│   └── gui.py                # CustomTkinter modern desktop GUI
└── tests/
    ├── __init__.py
    ├── test_cache.py         # Cache storage, TTL, clearing
    ├── test_cli.py           # CLI commands and options
    ├── test_client.py        # Retries, headers, timeouts
    ├── test_engine.py        # End-to-end engine crawling & pagination
    ├── test_exporter.py      # Export output verification
    ├── test_gui.py           # GUI initialization test
    ├── test_pagination.py    # Pagination strategies & loop detection
    ├── test_parser.py        # Selector extraction & type casting
    ├── test_rate_limiter.py  # Rate limiter intervals & jitter
    └── test_robots.py        # Robots.txt permissions
```

---

## Installation & Setup

1. Navigate to the project directory:
   ```bash
   cd 06-web-scraper
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```

3. Install dependencies and the package:
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```

---

## Command Line Usage

The tool provides the `scraper` and `web-scraper` commands.

### 1. Run a Custom Scrape Job

Scrape multiple pages using a container selector and field extraction rules:

```bash
scraper run https://quotes.toscrape.com \
  --container "div.quote" \
  -f "quote:span.text:text" \
  -f "author:small.author:text" \
  -f "author_url:span > a:href" \
  --strategy next_link \
  -n "li.next > a" \
  --pages 2 \
  --export scraped_data/quotes.json
```

Field definition syntax:
```text
name:selector[:extract[:cast]]
```
- `extract`: `text`, `href`, `src`, `html`, or `attr(custom-attr)`
- `cast`: `str`, `int`, `float`, `bool`, `list`

### 2. Run a Built-in Preset

List available presets:
```bash
scraper preset list
```

Run a preset (e.g. `quotes` or `books`):
```bash
scraper preset run quotes --pages 3 --export quotes.csv
scraper preset run books --pages 2 --export books.db
```

### 3. Test Selectors Interactively

Quickly inspect elements matching a selector on any page:
```bash
scraper test-selector https://quotes.toscrape.com "span.text" --limit 5
```

### 4. Verify Robots.txt

Check whether a URL is permitted for scraping under `robots.txt`:
```bash
scraper robots https://quotes.toscrape.com
```

### 5. Cache Management

Inspect disk cache statistics or purge cached responses:
```bash
scraper cache stats
scraper cache clear
```

---

## Desktop GUI

Launch the desktop interface using either:
```bash
scraper-gui
# or
python -m web_scraper.gui
```

### Features:
- **Preset Loader**: Instantly populate target settings for quotes, books, news, etc.
- **Rule Builder**: Add, configure, and delete field extraction rules interactively.
- **Selector Tester Tab**: Test any CSS selector against a target URL and inspect live matches before running a full scrape.
- **Live Output**: Real-time progress bar, request log stream, formatted results table, and formatted JSON viewer.
- **Export**: Export scraped data to JSON, CSV, Markdown, or SQLite via native file dialogs.

---

## Programmatic Python API

The engine can be embedded directly into Python scripts:

```python
from web_scraper.engine import ScraperEngine
from web_scraper.exporter import DataExporter
from web_scraper.models import ItemRule, PaginationConfig, ScrapeJob

job = ScrapeJob(
    url="https://quotes.toscrape.com",
    container_selector="div.quote",
    rules=[
        ItemRule(name="quote", selector="span.text", extract="text"),
        ItemRule(name="author", selector="small.author", extract="text"),
        ItemRule(name="author_link", selector="span > a", extract="href"),
    ],
    pagination=PaginationConfig(
        strategy="next_link",
        next_selector="li.next > a",
        max_pages=2,
    ),
    rate_limit_delay=0.5,
    respect_robots_txt=True,
    use_cache=True,
)

engine = ScraperEngine()
result = engine.run(job)

print(f"Scraped {result.total_items} items in {result.duration_seconds}s")
DataExporter.export_json(result.items, "output.json")
```

---

## Testing & Verification

Run the comprehensive test suite with `pytest`:

```bash
pytest -v
```

All 44 tests cover:
- Rate limiter timing, domain extraction, and jitter bounds
- Robots.txt parsing, allow/disallow evaluation, and crawl delays
- Response caching, TTL expiry, and disk persistence
- HTTP client retries on 503/429 status codes, backoff factors, and connection errors
- HTML parser CSS extraction, attribute extraction, regex extraction, and type casting
- Pagination strategies (next link, query param, offset, loop detection, quotas)
- Data exporters (JSON, JSONL, CSV, Markdown tables, SQLite database insertion)
- Click CLI commands and argument parsing
- Desktop GUI initialization
