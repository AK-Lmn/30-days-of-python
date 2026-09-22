# Day 11 — NexusPG: Enterprise Relational Feature Flag & Configuration Platform

An enterprise-grade, asynchronous REST API backed by PostgreSQL and SQLAlchemy 2.0, demonstrating advanced relational data modeling, migrations, foreign key cascades, complex multi-table joins, aggregations, and transactional persistence.

**Date:** Sep 22, 2026  
**Status:** ✅ Completed

---

## Overview

NexusPG extends the concept of feature flags into a production-ready, multi-tenant relational system. Built from the ground up on SQLAlchemy 2.0 Async and PostgreSQL, it models the hierarchical lifecycle of modern feature deployment: **Projects**, isolated **Environments**, multivariate **Flags**, environment-specific **State Overrides**, priority-ordered **Targeting Rules**, multi-attribute **Rule Conditions**, and many-to-many **Tags**.

### Key Highlights

- **Relational Data Modeling & Integrity**:
  - `Project` -> 1:N `Environment` (with unique `(project_id, key)` constraints).
  - `Project` -> 1:N `Flag` (with unique `(project_id, key)` constraints).
  - `Flag` <-> M:N `Tag` via `flag_tags` composite primary key junction table.
  - `Flag` -> 1:N `FlagEnvironmentState` (with unique `(flag_id, environment_id)` constraints).
  - `FlagEnvironmentState` -> 1:N `TargetingRule` -> 1:N `RuleCondition`.
  - Referential integrity with `ON DELETE CASCADE` across all child relationships.
- **Advanced Relational Queries & Aggregations**:
  - Eager relationship preloading (`selectinload`) to eliminate N+1 queries.
  - Multi-table filtering via `Flag.tags.any(...)` subquery exists clauses.
  - Relational aggregation queries: flag counts by type, tag distribution across projects, and per-environment health statistics (enabled vs. disabled counts and rule totals).
- **Alembic Database Migrations**:
  - Full schema version control with async engine migration runner (`alembic upgrade head`, `alembic downgrade base`).
- **Flexible Database Persistence**:
  - Production ready for PostgreSQL via `postgresql+asyncpg`.
  - Seamless offline/CI fallback to async SQLite (`sqlite+aiosqlite`) with enforced foreign keys (`PRAGMA foreign_keys=ON`).
  - Docker Compose service for instant 1-command PostgreSQL 16 local startup.
- **Deterministic Targeting Engine**:
  - Contextual targeting matching rules on attributes (`equals`, `in`, `contains`, `starts_with`, `ends_with`, numeric thresholds).
  - Deterministic SHA-256 bucketing for percentage-based rollouts.
- **Developer Experience**:
  - Interactive OpenAPI / Swagger UI at `/docs` and ReDoc at `/redoc`.
  - Rich CLI (`nexuspg`) for database migrations, seeding demo datasets, listing projects and flags, evaluating flags, and launching the server.
  - Automated test suite with 100% pass rate.

---

## Relational Architecture

```
                    ┌─────────────────────────┐
                    │        Project          │
                    │   id, key (UQ), name    │
                    └───────────┬─────────────┘
                                │ 1:N
            ┌───────────────────┴───────────────────┐
            │ 1:N                                   │ 1:N
 ┌──────────▼───────────────┐            ┌──────────▼───────────────┐
 │       Environment        │            │           Flag           │
 │ project_id, key (UQ_pair)│            │ project_id, key (UQ_pair)│
 └──────────┬───────────────┘            └─────┬──────────────┬─────┘
            │                                  │              │
            │          ┌───────────────────────┘              │ M:N
            │ 1:N      │ 1:N                                  │
 ┌──────────▼──────────▼───────────────┐          ┌───────────▼─────────────┐
 │       FlagEnvironmentState          │          │        FlagTag          │
 │ flag_id, env_id (UQ_pair), enabled  │          │    flag_id, tag_id      │
 └──────────────────┬──────────────────┘          └───────────┬─────────────┘
                    │ 1:N                                     │ M:N
         ┌──────────▼───────────────┐             ┌───────────▼─────────────┐
         │      TargetingRule       │             │           Tag           │
         │ priority, serve_val, pct │             │      id, name (UQ)      │
         └──────────┬───────────────┘             └─────────────────────────┘
                    │ 1:N
         ┌──────────▼───────────────┐
         │       RuleCondition      │
         │ attribute, op, values    │
         └──────────────────────────┘
```

---

## Project Structure

```text
11-postgresql-api/
├── README.md                   # Project documentation
├── pyproject.toml              # Build config and dependencies
├── requirements.txt            # Dependency specification
├── docker-compose.yml          # PostgreSQL 16 container definition
├── alembic.ini                 # Alembic configuration
├── .gitignore
├── nexuspg/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application factory & exception handling
│   ├── cli.py                  # Rich + Click CLI runner
│   ├── dependencies.py         # Request-scoped repository injection
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # Pydantic Settings
│   │   ├── errors.py           # Domain exceptions
│   │   ├── evaluator.py        # Rule matching and percentage bucketing engine
│   │   └── middleware.py       # Latency and request ID tracking
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py             # SQLAlchemy DeclarativeBase
│   │   ├── session.py          # Async engine and session factory
│   │   └── models.py           # Relational ORM models
│   ├── migrations/
│   │   ├── env.py              # Async migration runner
│   │   ├── script.py.mako      # Zero-comment migration template
│   │   └── versions/
│   │       └── 001_initial_schema.py # Initial database schema
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── project_repo.py     # Project and Environment queries
│   │   ├── flag_repo.py        # Flags, tags, states, and rules queries
│   │   ├── analytics_repo.py   # Multi-table aggregations and stats
│   │   └── audit_repo.py       # Audit log persistence
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── projects.py         # Projects & environments endpoints
│   │   ├── flags.py            # Flag CRUD & environment state updates
│   │   ├── evaluation.py       # Rule evaluation endpoints
│   │   ├── analytics.py        # Relational metrics endpoints
│   │   ├── audit.py            # Audit log endpoints
│   │   └── health.py           # Database ping and health check
│   └── schemas/
│       ├── __init__.py
│       ├── common.py           # Pagination and error envelopes
│       ├── project.py          # Project and Environment Pydantic models
│       ├── flag.py             # Flag, rule, condition, and tag schemas
│       ├── evaluation.py       # Evaluation request and response schemas
│       ├── analytics.py        # Analytics report schemas
│       └── audit.py            # Audit log schemas
└── tests/
    ├── __init__.py
    ├── conftest.py             # SQLite in-memory test fixtures
    ├── test_projects.py        # Project & environment tests
    ├── test_flags.py           # Flag CRUD & tagging tests
    ├── test_cascade.py         # Foreign key cascade deletion tests
    ├── test_evaluation.py      # Rule evaluation tests
    ├── test_analytics.py       # Aggregation query tests
    ├── test_health.py          # Health check tests
    └── test_migrations.py      # Alembic migration tests
```

---

## Installation & Setup

### 1. Create Virtual Environment and Install Dependencies

```powershell
uv venv
.\.venv\Scripts\activate
uv pip install -e ".[dev]"
```

### 2. Configure Database

#### Option A: PostgreSQL with Docker Compose (Recommended for Production)

```powershell
docker compose up -d
```

Set your connection string in `.env`:
```env
DATABASE_URL=postgresql+asyncpg://nexus:nexuspassword@localhost:5432/nexus_flags
```

#### Option B: Local Async SQLite (Default / Offline)

Leave `DATABASE_URL` unset or set to SQLite:
```env
DATABASE_URL=sqlite+aiosqlite:///nexuspg.db
```

### 3. Run Database Migrations

Apply Alembic migrations to construct all tables and indexes:

```powershell
nexuspg db migrate
```

Verify connection:
```powershell
nexuspg db ping
```

### 4. Seed Demo Data

Populate the relational schema with sample projects, environments, flags, targeting rules, and tags:

```powershell
nexuspg db seed
```

---

## Command-Line Interface (CLI)

The `nexuspg` CLI provides full management of the platform:

| Command | Description |
|---|---|
| `nexuspg serve` | Start the FastAPI Uvicorn server |
| `nexuspg db ping` | Verify database connectivity with `SELECT 1` |
| `nexuspg db init` | Initialize database schema directly |
| `nexuspg db migrate` | Apply Alembic schema migrations (`upgrade head`) |
| `nexuspg db rollback` | Downgrade Alembic schema (`downgrade -1`) |
| `nexuspg db seed` | Seed realistic demo projects, flags, and rules |
| `nexuspg projects list` | List all registered projects and environments |
| `nexuspg flags list --project <key>` | List flags, types, default values, and tags |
| `nexuspg evaluate --project <key> --env <key> --flag <key>` | Evaluate a flag against context |

### Evaluation Examples

Evaluate with user email matching an internal beta rule:
```powershell
nexuspg evaluate --project ecommerce-platform --env production --flag enable-instant-checkout --user-id u123 --attr email=tester@company.com
```
Output:
```text
Flag: enable-instant-checkout
Enabled: True
Value: True
Reason: RULE_MATCH: Internal Beta Testers
Rule ID: 5b44bde4-703f-4831-9efa-03ffaecaca0c
```

Evaluate with VIP customer tier matching a rule:
```powershell
nexuspg evaluate --project ecommerce-platform --env production --flag enable-instant-checkout --user-id u456 --attr tier=gold
```
Output:
```text
Flag: enable-instant-checkout
Enabled: True
Value: True
Reason: RULE_MATCH: VIP Tier Customers
```

---

## REST API Reference

### Health & Root
- `GET /` — Service metadata and documentation links.
- `GET /api/v1/health` — Database health check (`SELECT 1`).

### Projects & Environments
- `POST /api/v1/projects` — Create project (automatically provisions `development`, `staging`, and `production` environments).
- `GET /api/v1/projects` — Paginated list of projects.
- `GET /api/v1/projects/{project_key}` — Retrieve project with environments.
- `PATCH /api/v1/projects/{project_key}` — Update project name or description.
- `DELETE /api/v1/projects/{project_key}` — Delete project and cascade-delete all child environments, flags, states, and rules.
- `GET /api/v1/projects/{project_key}/environments` — List environments in project.
- `POST /api/v1/projects/{project_key}/environments` — Create a custom environment.
- `DELETE /api/v1/projects/{project_key}/environments/{env_key}` — Delete an environment.

### Flags & Configurations
- `POST /api/v1/projects/{project_key}/flags` — Create flag with tags.
- `GET /api/v1/projects/{project_key}/flags` — Paginated list of flags (supports `?tag=` and `?search=`).
- `GET /api/v1/projects/{project_key}/flags/{flag_key}` — Detailed flag view including environment states, rules, and conditions.
- `PATCH /api/v1/projects/{project_key}/flags/{flag_key}` — Update flag metadata and tags.
- `DELETE /api/v1/projects/{project_key}/flags/{flag_key}` — Delete flag.
- `GET /api/v1/projects/{project_key}/flags/{flag_key}/environments/{env_key}` — Retrieve environment configuration for a flag.
- `PUT /api/v1/projects/{project_key}/flags/{flag_key}/environments/{env_key}` — Update enabled status, rollout percentage, variant value, and targeting rules.

### Evaluation
- `POST /api/v1/projects/{project_key}/environments/{env_key}/evaluate/{flag_key}` — Evaluate a single flag against evaluation context (`user_id`, `attributes`).
- `POST /api/v1/projects/{project_key}/environments/{env_key}/evaluate` — Bulk evaluate flags.

### Analytics & Audit
- `GET /api/v1/projects/{project_key}/analytics` — Aggregated relational metrics: flag type counts, tag distribution, and environment health.
- `GET /api/v1/audit` — Paginated audit log of entity modifications.

---

## Running the Automated Test Suite

Run pytest in the isolated virtual environment:

```powershell
pytest -v
```

### Test Coverage Highlights
- **15 automated tests** covering:
  - Project creation, key uniqueness constraints, environment provisioning.
  - Flag creation, many-to-many tag associations, query filtering.
  - Foreign key cascade deletions across the entire relational tree.
  - Multi-condition targeting rule evaluation and percentage rollouts.
  - Complex relational SQL aggregations and reporting.
  - Alembic schema migrations (`upgrade head` -> `downgrade base` -> `upgrade head`).
  - Health check endpoint and database connectivity.
- **Zero comments rule compliance**: Verified 100% clean across all Python source and test files.
