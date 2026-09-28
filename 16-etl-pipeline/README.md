# Day 16 — PipeForge: Production-Grade ETL Pipeline

A modular, extensible, and high-throughput Extract-Transform-Load (ETL) pipeline engine built with Python 3.13, Pydantic V2, SQLAlchemy, Click, Rich, and PyYAML. PipeForge extracts heterogeneous data from real-world sources (CSV, JSON, JSON Lines, REST APIs, SQL databases), validates records with strict schema enforcement and dataset-level quality gates, applies composable transformation and anonymization chains, and loads cleaned data into destinations (SQLite/SQL with UPSERT support, CSV, JSON, and external REST APIs) while tracking run audit history and segregating failed records in a quarantine dead-letter repository.

**Date:** Sep 27, 2026  
**Status:** ✅ Complete  

---

## Architecture Overview

```
                                 DATA SOURCES
              [CSV / TSV]   [JSON / JSONL]   [REST APIs]   [SQL Databases]
                   │               │              │               │
                   └───────┬───────┴──────────────┴───────┬───────┘
                           │                              │
                           ▼                              ▼
                 ┌──────────────────────────────────────────────────┐
                 │                EXTRACT LAYER                     │
                 │  • Dialect & Delimiter Auto-Detection            │
                 │  • Streaming & Chunked Execution (Low Memory)    │
                 │  • REST API Pagination (Page, Offset, Cursor)    │
                 │  • Exponential Backoff & Connection Retries      │
                 └─────────────────────────┬────────────────────────┘
                                           │
                                           ▼
                 ┌──────────────────────────────────────────────────┐
                 │         VALIDATE & QUALITY GATES                 │
                 │  • Schema Enforcement & Type Coercion (Pydantic) │
                 │  • Field Rules (Email, Range, Regex, NotEmpty)   │
                 │  • Error Strategy: FAIL_FAST, QUARANTINE, SKIP   │
                 │  • Dead-Letter Quarantine & Audit Persistence    │
                 │  • Quality Gates: Null %, Duplication, Error %   │
                 └──────────────┬──────────────────────┬────────────┘
                                │                      │
                 (Quarantined)  │                      │ (Valid Records)
                                ▼                      ▼
                       ┌────────────────┐    ┌───────────────────────────┐
                       │ Quarantine DB  │    │     TRANSFORM LAYER       │
                       │ & JSON Export  │    │  • String Cleaning/Spaces │
                       └────────────────┘    │  • Case Normalization     │
                                             │  • Date Standard ISO-8601 │
                                             │  • Field Renaming/Picking │
                                             │  • Derived Calculated Cols│
                                             │  • Categorical Mapping    │
                                             │  • PII Masking & Hashing  │
                                             │  • Stateful Deduplication │
                                             │  • Group By Aggregations  │
                                             └─────────────┬─────────────┘
                                                           │
                                                           ▼
                 ┌──────────────────────────────────────────────────┐
                 │                  LOAD LAYER                      │
                 │  • SQLite / Relational DB (APPEND/REPLACE/UPSERT)│
                 │  • Auto-Inferred Schema & Dynamic Table Creation │
                 │  • CSV Destination with Automatic Headers        │
                 │  • Structured JSON / JSON Lines Sink             │
                 │  • Outbound REST Webhook / API Batch Dispatch    │
                 └─────────────────────────┬────────────────────────┘
                                           │
                                           ▼
                 ┌──────────────────────────────────────────────────┐
                 │            AUDIT & PERSISTENCE STORE             │
                 │  • Run Metrics, Timestamps, Duration & Rec/sec   │
                 │  • Per-Run Quarantine Inspection & Replay        │
                 │  • Rich Terminal Dashboard & Reporting           │
                 └──────────────────────────────────────────────────┘
```

---

## Key Features

1. **Multi-Source Extraction**
   - **CSV / TSV**: Automatic delimiter sniffing (`csv.Sniffer`), whitespace trimming, encoding error recovery, and streaming dictionary generation.
   - **JSON / JSON Lines**: Handles both nested arrays in objects and line-delimited `.jsonl` streaming for large datasets.
   - **REST APIs**: Paginates via page number (`page`/`per_page`), offset/limit (`offset`/`limit`), or cursor-based tokens with HTTP status retry backoff.
   - **SQL Databases**: Direct streaming cursor execution over SQLAlchemy connections (SQLite, PostgreSQL, MySQL) with chunked memory fetching.

2. **Validation & Quality Assurance**
   - **Pydantic Schema Validation**: Automatically enforces types, constraints, and coerces string inputs into typed fields.
   - **Field Rule Engine**: Modular rules for `NotEmptyRule`, `RangeRule`, `RegexRule`, `EmailRule`, and `InListRule`.
   - **Dataset Quality Gates**: Prevents dirty batches from corrupting production destinations by validating overall dataset error rates, maximum null percentages per field, minimum record counts, and column uniqueness.
   - **Quarantine Handling**: Bad rows are isolated into an SQLite quarantine store with full error diagnostics and row numbers, allowing pipeline processing to continue without silent data corruption.

3. **Composable Transformation Engine**
   - **Normalizers**: `StringCleaner`, `CaseNormalizer`, `DateNormalizer` (standardizing 10+ arbitrary date formats into ISO-8601), and `TypeCaster`.
   - **Mappers & Derivations**: `FieldRenamer`, `FieldPicker`, `FieldRemover`, `ValueMapper`, and `DerivedField` (computed arithmetic or custom lambdas).
   - **PII Anonymization**: `FieldAnonymizer` with SHA-256 salted hashing, email masking (`j***@example.com`), phone masking (`***-***-1234`), and string redaction.
   - **Stateful Deduplication**: `Deduplicator` eliminates duplicate rows using single or composite key sets.
   - **Batch Aggregations**: `BatchAggregator` supports `sum`, `avg`, `min`, `max`, and `count` grouped across arbitrary keys.

4. **Reliable Destination Loading**
   - **Database Loader**: Supports `APPEND`, `REPLACE`, and SQLite/PostgreSQL `UPSERT` using primary key index elements. Automatically reflects or creates table structures on demand.
   - **File Sinks**: Structured CSV and JSON/JSONL exporters.
   - **REST API Loader**: Dispatches batches to downstream webhooks and ingestion APIs with automatic retries.

5. **Execution Tracking & CLI Dashboard**
   - Complete execution history tracking start time, records read/valid/invalid/loaded/quarantined, execution duration, and throughput (rec/sec).
   - Rich CLI interface for running pipelines, profiling data sources, reviewing past execution runs, and exporting quarantined records.

---

## Project Structure

```text
16-etl-pipeline/
├── pipeforge/
│   ├── __init__.py
│   ├── config.py                 # Application settings
│   ├── cli.py                    # Click & Rich CLI entrypoint
│   ├── models/
│   │   ├── __init__.py
│   │   ├── enums.py              # Statuses, LoadModes, ErrorStrategies
│   │   ├── record.py             # Record entity and metadata
│   │   ├── metrics.py            # Execution statistics & throughput
│   │   └── history.py            # SQLAlchemy models for audit history
│   ├── storage/
│   │   ├── __init__.py
│   │   └── audit_store.py        # Persistent run & quarantine store
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── base.py               # BaseExtractor abstract interface
│   │   ├── csv_extractor.py      # CSV / TSV extractor
│   │   ├── json_extractor.py     # JSON and JSONL extractor
│   │   ├── api_extractor.py      # REST API pagination extractor
│   │   └── sql_extractor.py      # Database query extractor
│   ├── validators/
│   │   ├── __init__.py
│   │   ├── base.py               # BaseValidator interface
│   │   ├── rules.py              # Built-in field validation rules
│   │   ├── schema_validator.py   # Pydantic schema validation
│   │   └── quality_gate.py       # Batch-level quality gate evaluation
│   ├── transformers/
│   │   ├── __init__.py
│   │   ├── base.py               # BaseTransformer interface
│   │   ├── chain.py              # Sequentially chained transformations
│   │   ├── normalizers.py        # String, date, case, and type normalizers
│   │   ├── mappers.py            # Renaming, picking, derived fields, filters
│   │   ├── anonymizer.py         # PII masking and SHA-256 hashing
│   │   ├── deduplicator.py       # Stateful record deduplication
│   │   └── aggregator.py         # Group-by batch aggregation
│   ├── loaders/
│   │   ├── __init__.py
│   │   ├── base.py               # BaseLoader interface
│   │   ├── database_loader.py    # SQLite/SQL APPEND, REPLACE, UPSERT
│   │   ├── csv_loader.py         # CSV file sink
│   │   ├── json_loader.py        # JSON & JSONL file sink
│   │   └── api_loader.py         # REST endpoint loader
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── pipeline.py           # Pipeline runner & batch coordinator
│   │   └── yaml_parser.py        # Declarative YAML pipeline parser
│   └── samples/
│       ├── __init__.py
│       └── generator.py          # Mock dataset generator
├── tests/
│   ├── __init__.py
│   ├── test_extractors.py
│   ├── test_validators.py
│   ├── test_transformers.py
│   ├── test_loaders.py
│   ├── test_engine.py
│   └── test_cli.py
├── pipeline.example.yaml         # Complete declarative pipeline config
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Installation & Setup

1. **Navigate to Day 16 folder:**
   ```bash
   cd 16-etl-pipeline
   ```

2. **Create and activate virtual environment:**
   ```powershell
   uv venv
   .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```powershell
   uv pip install -e .
   ```

---

## CLI Usage Guide

### 1. Generate Sample Datasets
```powershell
# Generate 100 sample e-commerce orders (includes dirty records for quarantine testing)
pipeforge sample-data --type orders --count 100 --output sample_orders.csv

# Generate 50 sample users in JSON Lines format
pipeforge sample-data --type users --count 50 --lines --output sample_users.jsonl
```

### 2. Inspect & Profile a Data Source
```powershell
pipeforge inspect --source sample_orders.csv --rows 5
```

### 3. Run a Declarative Pipeline
```powershell
pipeforge run --config pipeline.example.yaml
```

### 4. Run an Ad-hoc Pipeline (Quick Mode)
```powershell
pipeforge run --source sample_orders.csv --dest warehouse.db --strategy QUARANTINE
```

### 5. Review Execution History
```powershell
pipeforge history --limit 10
```

### 6. Inspect & Export Quarantined Records
```powershell
# List quarantined records for a run
pipeforge quarantine list <RUN_ID>

# Export all quarantined records with error metadata to JSON
pipeforge quarantine export <RUN_ID> --output quarantine/failed_records.json
```

---

## Declarative YAML Pipeline Specification

Pipelines can be configured declaratively:

```yaml
name: "ecommerce_sales_pipeline"
batch_size: 100
error_strategy: "QUARANTINE"

source:
  type: "csv"
  path: "sample_orders.csv"
  delimiter: ","
  encoding: "utf-8"

validation:
  rules:
    - type: "not_empty"
      field: "order_id"
    - type: "email"
      field: "customer_email"
    - type: "range"
      field: "price"
      min: 0.01

transformations:
  - type: "clean_string"
    fields: ["customer_name", "product", "category"]
    strip: true
  - type: "normalize_case"
    fields: ["category", "status"]
    mode: "lower"
  - type: "cast"
    types:
      price: "float"
      quantity: "int"
  - type: "derive"
    field: "total_amount"
    expression: "round(price * quantity, 2)"
  - type: "anonymize"
    fields: ["customer_email"]
    strategy: "mask_email"

destinations:
  - type: "sqlite"
    connection_url: "sqlite:///warehouse.db"
    table: "orders_clean"
    mode: "REPLACE"
    primary_keys: ["order_id"]
  - type: "json"
    path: "data_output/orders_clean.json"
    mode: "REPLACE"
```

---

## Testing

Run the full pytest suite:

```powershell
pytest -v
```

All 45 tests verify:
- Extractors (CSV, JSON, JSONL, SQL, REST API)
- Validators & Quality Gates
- Transformers (Normalizers, Mappers, Derivations, Anonymizers, Deduplication, Aggregations)
- Loaders (SQLite with APPEND/REPLACE/UPSERT, CSV, JSON, REST API)
- Engine Execution (Error strategies, Quarantine tracking, YAML parsing)
- CLI Commands (`run`, `inspect`, `sample-data`, `history`, `quarantine`)
