# Day 17 — CleanForge: Autonomous Data Cleaning Engine

An autonomous, extensible, and high-performance data cleaning and remediation engine built with Python 3.13, Pydantic V2, Click, Rich, and PyYAML. CleanForge ingests dirty, inconsistent CSV, TSV, JSON, and JSON Lines datasets, automatically detects dialects and encodings, infers column types, computes dataset health scores, applies composable transformation and imputation pipelines, segregates non-compliant records into quarantine dead-letter stores, and generates comprehensive remediation audit reports.

**Date:** Sep 28, 2026  
**Status:** ✅ Complete  

---

## Architecture Overview

```
                               RAW DATA INGESTION
               [Dirty CSV]   [TSV Files]   [Nested JSON]   [JSON Lines]
                    │             │              │               │
                    └───────┬─────┴──────────────┴───────┬───────┘
                            │                            │
                            ▼                            ▼
                 ┌──────────────────────────────────────────────────┐
                 │                IO & INGESTION LAYER              │
                 │  • Delimiter Sniffing (Comma, Semi, Tab, Pipe)   │
                 │  • Encoding Detection (UTF-8, UTF-8-SIG, Latin1) │
                 │  • Nested Object Flattening (Dot Notation)       │
                 │  • Streaming & Record Normalization              │
                 └─────────────────────────┬────────────────────────┘
                                           │
                                           ▼
                 ┌──────────────────────────────────────────────────┐
                 │              PROFILER & DIAGNOSTICS              │
                 │  • Type Inference (Int, Float, Date, Email, etc.)│
                 │  • Statistical Metrics (Mean, Median, Mode, SD)  │
                 │  • Whitespace & Casing Diagnostics               │
                 │  • Dataset Health Score Calculation (0-100%)     │
                 └─────────────────────────┬────────────────────────┘
                                           │
                                           ▼
                 ┌──────────────────────────────────────────────────┐
                 │             CLEANING & PIPELINE ENGINE           │
                 │  • Header Normalization (snake, camel, kebab)    │
                 │  • Missing Value Imputation (Mean, Median, Fill) │
                 │  • Deduplication (Exact & Fuzzy SequenceMatcher) │
                 │  • Text Sanitization & Unicode Normalization     │
                 │  • Currency, Percent & Numeric Formatting        │
                 │  • Multi-Format Date/Time Standardization        │
                 │  • Phone (E.164) & Email Sanitization            │
                 │  • Outlier Remediation (IQR & Z-Score Clipping)  │
                 │  • Rule Constraints & Validation Gates           │
                 └──────────────┬──────────────────────┬────────────┘
                                │                      │
                 (Quarantined)  │                      │ (Clean Records)
                                ▼                      ▼
                       ┌────────────────┐    ┌────────────────────┐
                       │ Quarantine Sink│    │    Clean Export    │
                       │ & Reason Audit │    │ CSV, TSV, JSON, L  │
                       └────────────────┘    └─────────┬──────────┘
                                                       │
                                                       ▼
                 ┌──────────────────────────────────────────────────┐
                 │             AUDIT & REMEDIATION REPORT           │
                 │  • Before vs After Health Score Delta            │
                 │  • Per-Column Modification Counts                │
                 │  • Deduplication & Imputation Metrics            │
                 │  • Markdown & JSON Remediation Summaries         │
                 └──────────────────────────────────────────────────┘
```

---

## Key Features

1. **Multi-Format Ingestion with Auto-Detection**
   - Ingests CSV, TSV, JSON (arrays, root wrappers, or single records), and JSON Lines (`.jsonl`, `.ndjson`).
   - Automated delimiter sniffing (comma, semicolon, tab, pipe) and character encoding detection (`utf-8`, `utf-8-sig`, `latin-1`, `cp1252`).
   - Deep nested JSON flattening into flat records with customizable dot notation separators.

2. **Dataset Profiling & Quality Scoring**
   - Automatically classifies column types: `integer`, `float`, `boolean`, `date`, `datetime`, `email`, `phone`, `url`, `uuid`, and `string`.
   - Computes statistical summaries including null counts/percentages, unique value ratios, minimums, maximums, means, medians, modes, and standard deviations.
   - Diagnoses whitespace inconsistencies (leading, trailing, and internal multi-spaces).
   - Generates an overall 0–100% Dataset Health Score evaluating completeness, uniqueness, and format consistency.

3. **Header Standardization**
   - Converts arbitrary and messy headers into clean identifiers (`snake_case`, `camelCase`, `kebab-case`, `lower`, `upper`, `title`).
   - Strips whitespace, eliminates illegal special characters, handles deduplication of collided column names (`col_1`, `col_2`), and supports explicit column renaming maps.

4. **Missing Value Imputation & Handling**
   - Identifies null representations (`""`, `"NA"`, `"N/A"`, `"null"`, `"None"`, `"-"`, `"?"`, `"NaN"`).
   - Configurable imputation strategies: `constant`, `mean`, `median`, `mode`, `forward_fill`, `backward_fill`, or `drop_row`.
   - Dataset-level drop thresholds based on missing field percentage.

5. **Exact & Fuzzy Deduplication**
   - Deduplicates across all fields or designated key subsets.
   - Configurable retention policies: keep `first`, `last`, or drop `none`.
   - High-performance fuzzy deduplication using string similarity algorithms (`difflib.SequenceMatcher`) to merge near-duplicates caused by typos or minor discrepancies.

6. **Text Sanitization & Normalization**
   - Leading/trailing whitespace trimming and multi-space collapsing.
   - Unicode `NFKC` normalization and HTML tag stripping.
   - Regex-based text replacements and case standardizations.

7. **Numeric, Currency, & Percent Parsing**
   - Strips currency symbols (`$`, `€`, `£`, `¥`, `₹`, `₩`, etc.) and formatting characters.
   - Resolves thousand separators and European decimal commas (`1.234,56` vs `1,234.56`).
   - Converts percentage strings (`15.5%` -> `0.155`).
   - Rounds to configurable decimal precision with fallback defaults on parse failure.

8. **Heterogeneous Date & Time Normalization**
   - Parses varied date formats (`YYYY-MM-DD`, `DD/MM/YYYY`, `MM/DD/YYYY`, `Month DD, YYYY`, ISO-8601 timestamps, etc.).
   - Standardizes values to a uniform target format (e.g. `%Y-%m-%d` or `%Y-%m-%dT%H:%M:%SZ`).

9. **Contact Info Sanitization (Email & Phone)**
   - Normalizes telephone numbers into E.164 (`+15551234567`), US Standard (`(555) 123-4567`), or plain digit strings.
   - Validates RFC-compliant email formats with automatic lowercase casting and optional quarantine of malformed addresses.

10. **Outlier Detection & Remediation**
    - Interquartile Range (`IQR`: Q1 - 1.5*IQR to Q3 + 1.5*IQR) and Z-Score (|z| > threshold) detection.
    - Remediation actions: clip to boundaries, set to null, replace with median/mean, or drop the offending row.

11. **Validation Gates & Dead-Letter Quarantine**
    - Enforces numeric range boundaries, enum/allowed value constraints, regex patterns, and not-null requirements.
    - Non-compliant records are segregated into a quarantine output file annotated with exact violation reasons.

12. **Remediation Audit Reporting**
    - Tracks before/after quality metrics, duration, number of rows dropped or imputed, and exact counts of modifications made per column.
    - Generates human-readable Markdown and structured JSON audit reports.

13. **Declarative Recipes & Fluent Builder API**
    - Configure clean pipelines declaratively via YAML or JSON.
    - Pre-packaged presets: `standard`, `customer`, and `ecommerce`.
    - Fluent Python chaining API (`CleanBuilder`) for programmatic workflows.

---

## Installation & Setup

CleanForge runs on Python 3.10+ (tested with Python 3.13):

```powershell
cd 17-data-cleaning
uv venv .venv
.venv\Scripts\activate
uv pip install -e ".[dev]"
```

---

## Command Line Interface (CLI)

The `cleanforge` command-line utility provides five main commands:

### 1. `inspect` — Profile & Diagnose a Dataset
Inspect an existing CSV or JSON dataset to evaluate column types, missingness, unique counts, whitespace issues, and the dataset health score:

```powershell
cleanforge inspect dirty_sample.csv
```

### 2. `clean` — Clean a Dataset with Recipes or Presets
Clean a messy dataset and output cleaned records, an audit report, and quarantined invalid records:

```powershell
cleanforge clean messy.csv -o clean.csv -p customer -q quarantine.csv --report audit.md
```

Options:
- `-o, --output PATH`: Target path for cleaned data (required).
- `-r, --recipe PATH`: Custom YAML or JSON cleaning recipe.
- `-p, --preset [standard|customer|ecommerce]`: Built-in recipe preset.
- `-q, --quarantine PATH`: Destination file for rejected records.
- `--report PATH`: Markdown or JSON path for the remediation audit report.

### 3. `diff` — Compare Data Quality Before and After
Display a side-by-side comparison table showing row count changes, dropped duplicates, and health score improvements:

```powershell
cleanforge diff messy.csv clean.csv
```

### 4. `sample` — Generate Dirty Test Datasets
Generate realistic messy data containing casing inconsistencies, dirty dates, mixed phone formats, invalid emails, currency strings, outliers, and duplicates:

```powershell
cleanforge sample -n 100 -o sample_dirty.csv
```

### 5. `recipe-init` — Generate Recipe Templates
Scaffold a starter YAML or JSON recipe:

```powershell
cleanforge recipe-init -p customer -o my_recipe.yaml
```

---

## Programmatic Usage: Fluent Builder API

CleanForge provides an intuitive, chainable `CleanBuilder` interface:

```python
from cleanforge import CleanBuilder
from cleanforge.models.types import CasingType, DuplicateKeep, ImputeStrategy, OutlierMethod, OutlierStrategy

builder = CleanBuilder()
builder.load("messy_customers.csv")

report = (
    builder
    .standardize_headers(casing=CasingType.SNAKE)
    .drop_duplicates(subset=["email"], keep=DuplicateKeep.FIRST)
    .handle_missing(
        column_strategies={
            "city": (ImputeStrategy.CONSTANT, "Unknown"),
            "account_balance": (ImputeStrategy.MEDIAN, None),
        }
    )
    .clean_text(columns=["first_name", "last_name", "city"], casing=CasingType.TITLE, strip=True)
    .clean_emails(columns=["email"], lowercase=True, action_on_invalid="quarantine")
    .clean_phones(columns=["phone"], phone_format="e164")
    .clean_dates(columns=["signup_date"], target_format="%Y-%m-%d")
    .clean_numbers(columns=["account_balance"], strip_currency=True, decimals=2)
    .handle_outliers(columns=["account_balance"], method=OutlierMethod.IQR, strategy=OutlierStrategy.CLIP)
    .save(
        output_path="cleaned_customers.csv",
        quarantine_path="quarantined_records.csv",
        report_path="cleaning_audit.md",
    )
)

print(f"Initial Health: {report.initial_health_score}% -> Final Health: {report.final_health_score}%")
```

---

## Declarative Recipe Specification

CleanForge recipes can be specified in YAML or JSON format:

```yaml
name: customer_cleaning_recipe
version: "1.0"
headers:
  casing: snake
  strip_whitespace: true
  remove_special_characters: true
  rename:
    email_address: email
    phone_number: phone

missing:
  missing_values: ["", "na", "n/a", "null", "none", "-"]
  default_strategy: forward_fill
  columns:
    city:
      strategy: constant
      fill_value: Unknown

duplicates:
  enabled: true
  subset: ["email"]
  keep: first
  fuzzy: true
  similarity_threshold: 0.90
  fuzzy_columns: ["first_name", "last_name"]

text:
  - columns: ["first_name", "last_name", "city"]
    strip: true
    collapse_spaces: true
    casing: title
    normalize_unicode: true

emails:
  - columns: ["email"]
    lowercase: true
    action_on_invalid: quarantine

phones:
  - columns: ["phone"]
    format: e164
    default_country_code: "1"

dates:
  - columns: ["signup_date"]
    target_format: "%Y-%m-%d"

numbers:
  - columns: ["account_balance"]
    strip_currency: true
    remove_commas: true
    target_type: float
    decimals: 2

outliers:
  - columns: ["account_balance"]
    method: iqr
    strategy: clip
    threshold: 1.5

validations:
  - column: email
    not_null: true
    action: quarantine
```

---

## Testing & Quality Assurance

The test suite contains 45 unit, integration, and CLI tests verifying every engine component.

Run the test suite with `pytest`:

```powershell
pytest -v
```

Test breakdown:
- `tests/test_profiler.py`: Type inference, metric calculations, whitespace diagnostics, health scoring.
- `tests/test_cleaners.py`: Casing transformations, missing value imputations, text sanitization, dates, booleans, numbers, phones, emails, outliers, validation rules.
- `tests/test_fuzzy_dedup.py`: SequenceMatcher fuzzy string deduplication and empty field guards.
- `tests/test_io.py`: Multi-dialect CSV/TSV reading/writing, JSON flattening, encoding sniffing, recipe persistence.
- `tests/test_pipeline.py`: CleanEngine orchestration, fluent CleanBuilder API, audit report exports.
- `tests/test_cli.py`: Click CLI commands (`inspect`, `clean`, `diff`, `sample`, `recipe-init`).

---

## Code Standards & Philosophy

In accordance with repository guidelines:
- **Zero Comments & Zero Docstrings**: All code files (`.py`) contain zero inline comments, zero block comments, and zero docstrings. Code readability is achieved strictly through clean architecture, explicit function/variable naming, and static type annotations.
- **Strict Folder Isolation**: All dependencies, virtual environments, configuration, and implementation artifacts reside exclusively inside `17-data-cleaning/`.
