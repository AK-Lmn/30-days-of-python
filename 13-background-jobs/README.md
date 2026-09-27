# Day 13 — TaskForge: Distributed Background Job Processing System

A production-grade, asynchronous background job processing system featuring priority queueing, delayed job scheduling, exponential backoff retries, dead-letter queues, worker heartbeat tracking, and a RESTful management API built with FastAPI, SQLAlchemy 2.0 (asyncio), and Python 3.13.

**Date:** Sep 24, 2026  
**Status:** ✅ Completed

---

## Overview

TaskForge decouples long-running, CPU-intensive, and I/O-heavy operations from the synchronous web request-response cycle. It provides reliable task execution, automatic retries with exponential backoff, progress tracking, scheduled delayed jobs, recurring cron tasks, and real-time worker health telemetry.

### Key Highlights

- **Robust Job State Machine**:
  - `pending`: Ready in queue for an available worker.
  - `scheduled`: Delayed execution awaiting a future trigger timestamp.
  - `running`: Actively processing within a worker process.
  - `completed`: Successfully executed with persisted result payload and 100% progress.
  - `retrying`: Failed with retries remaining; waiting for exponential backoff window.
  - `dead_letter`: Exhausted all retry attempts; archived for operator inspection.
  - `cancelled`: Manually aborted prior to or during processing.
  - `failed`: Non-retryable execution error with full captured exception traceback.
- **Priority & Multi-Queue Routing**:
  - Numerical priority scoring (1 to 100, where higher numbers are claimed first).
  - Multi-queue isolation (e.g., `default`, `high-priority`, `emails`, `reports`).
  - Worker queue binding: workers can listen to one or multiple specific queues.
- **Resilient Retry & Backoff Mechanics**:
  - Configurable maximum retries (`max_retries`) and base retry delay (`retry_delay_seconds`).
  - Exponential backoff algorithm: `delay = base_delay * (2 ^ retry_count)`.
  - Automatic routing to Dead Letter Queue (DLQ) when retry limits are reached.
- **Task Registry & Execution Context**:
  - Clean `@task` decorator registering both async coroutines and sync callables.
  - Synchronous functions automatically dispatched via `asyncio.to_thread`.
  - `ExecutionContext` injection providing live progress updates (`0%` to `100%`) and step descriptions.
  - Per-task timeout enforcement using `asyncio.wait_for`.
- **Built-in Task Handlers**:
  - `send_email`: Email dispatch with DNS resolution and SMTP handshake simulation.
  - `generate_report`: Multi-chunk dataset aggregation with progress reporting.
  - `resize_image`: Image downloading, resampling, and format optimization.
  - `data_export`: Asynchronous collection querying and CSV packaging.
  - `cleanup_expired_sessions`: Scheduled maintenance token pruning.
  - `slow_task` & `failing_task`: Benchmarking, timeouts, and fault-injection testing.
- **Scheduler Engine (Delayed & Recurring Cron)**:
  - Background tick engine monitoring delayed jobs and recurring definitions.
  - Interval-based recurring schedules (seconds).
  - Standard 5-part Unix cron expressions via `croniter` (e.g. `0 2 * * *`).
- **RESTful Management API**:
  - Interactive OpenAPI / Swagger UI at `/docs` and ReDoc at `/redoc`.
  - Full CRUD for jobs, cancellation, manual retry, queue metrics, and schedules.
- **Rich Operator CLI (`taskforge`)**:
  - Command-line tools for running workers, schedulers, servers, enqueuing jobs, inspecting status, and viewing queue dashboards.

---

## Repository Structure

```text
13-background-jobs/
├── pyproject.toml              # Build metadata, dependencies, and CLI entry point
├── requirements.txt            # Pinned requirements
├── README.md                   # Project documentation
├── .gitignore                  # Git ignore rules
├── .python-version             # Python version specification (3.13)
├── taskforge/
│   ├── __init__.py             # Package exports and version
│   ├── config.py               # Pydantic Settings configuration
│   ├── database.py             # Async SQLAlchemy engine and session factory
│   ├── main.py                 # FastAPI application factory and lifespan
│   ├── cli.py                  # Click and Rich terminal interface
│   ├── core/
│   │   ├── __init__.py         # Core domain exports
│   │   ├── enums.py            # JobStatus, Priority, ScheduleType
│   │   ├── exceptions.py       # Domain exception hierarchy
│   │   ├── executor.py         # ExecutionContext and progress reporter
│   │   ├── registry.py         # TaskRegistry, task decorator, definition
│   │   ├── scheduler.py        # Periodic interval & cron scheduler engine
│   │   └── worker.py           # Worker loop, claiming, semaphore concurrency
│   ├── models/
│   │   ├── __init__.py         # Model package exports
│   │   ├── db_models.py        # SQLAlchemy models (JobModel, WorkerModel, ScheduleModel)
│   │   └── schemas.py          # Pydantic v2 validation & response schemas
│   ├── repositories/
│   │   ├── __init__.py         # Repository exports
│   │   └── job_repo.py         # Atomic job queries, claiming, metrics, DLQ
│   ├── routers/
│   │   ├── __init__.py         # Router exports
│   │   ├── jobs.py             # /api/v1/jobs endpoints
│   │   ├── queues.py           # /api/v1/queues metrics endpoints
│   │   ├── schedules.py        # /api/v1/schedules recurring schedules
│   │   └── workers.py          # /api/v1/workers heartbeat tracking
│   └── tasks/
│       ├── __init__.py         # Built-in tasks exports
│       └── builtins.py         # Registered task implementations
└── tests/
    ├── __init__.py
    ├── conftest.py             # Test database engine and async client fixtures
    ├── test_registry.py        # Task registration & execution unit tests
    ├── test_worker.py          # Worker claiming, retries, DLQ, timeouts
    ├── test_scheduler.py       # Delay promotion & cron recurrence tests
    ├── test_api_jobs.py        # REST API job management tests
    ├── test_api_queues.py      # Queue stats, worker heartbeat, health tests
    └── test_cli.py             # Click CLI runner tests
```

---

## Job State Lifecycle

```text
               ┌─────────────┐
               │  SCHEDULED  │ (delayed / future timestamp)
               └──────┬──────┘
                      │ time reached
                      ▼
 ┌─────────────┐   ┌─────────────┐   Worker Claims   ┌─────────────┐
 │ POST /jobs  ├──►│   PENDING   ├──────────────────►│   RUNNING   │
 └─────────────┘   └─────────────┘                   └──────┬──────┘
                          ▲                                 │
                          │                                 │
                   Manual │ Retry            ┌──────────────┴──────────────┐
                          │                  ▼                             ▼
                   ┌──────┴──────┐    ┌─────────────┐               ┌─────────────┐
                   │   CANCELLED │    │  COMPLETED  │               │   FAILED    │
                   └─────────────┘    └─────────────┘               └──────┬──────┘
                                                                           │
                                                                   Retries │ Exceeded
                                                      ┌─────────────┐      │
                                                      │  RETRYING   │◄─────┤
                                                      └──────┬──────┘      │
                                                             │             ▼
                                                             │      ┌─────────────┐
                                                             └─────►│ DEAD_LETTER │
                                                                    └─────────────┘
```

---

## Installation & Setup

### 1. Initialize Virtual Environment

```powershell
uv venv
.venv\Scripts\activate
uv pip install -e ".[dev]"
```

### 2. Initialize the Database

```powershell
taskforge init-db
```

### 3. Inspect Registered Tasks

```powershell
taskforge tasks
```

---

## CLI Reference

TaskForge provides an interactive CLI powered by Click and Rich:

| Command | Arguments / Options | Description |
|---|---|---|
| `taskforge server` | `--host`, `--port`, `--reload` | Start the FastAPI REST API server |
| `taskforge worker` | `-q, --queue`, `-c, --concurrency`, `--worker-id` | Start background worker process |
| `taskforge scheduler` | `--poll-interval` | Start delayed and cron scheduler |
| `taskforge enqueue` | `<task_name>`, `-p, --payload`, `-q, --queue`, `--priority`, `--delay`, `--max-retries` | Enqueue a new background task |
| `taskforge status` | `<job_id>` | Show detailed progress and status of a job |
| `taskforge list` | `-q, --queue`, `-s, --status`, `-t, --task`, `-l, --limit` | List jobs in terminal table |
| `taskforge cancel` | `<job_id>` | Abort a pending or running job |
| `taskforge retry` | `<job_id>` | Re-queue a failed or dead-letter job |
| `taskforge stats` | — | Display live queue statistics and active workers |
| `taskforge tasks` | — | List all registered tasks in TaskRegistry |

---

## REST API Reference

All endpoints are prefixed with `/api/v1` and documented interactively at `/docs`.

### Jobs

- `POST /api/v1/jobs`: Enqueue a new job.
- `GET /api/v1/jobs`: List jobs with pagination (`offset`, `limit`) and filters (`queue`, `status`, `task_name`).
- `GET /api/v1/jobs/{job_id}`: Fetch job details, state, progress, and execution results.
- `POST /api/v1/jobs/{job_id}/cancel`: Cancel a pending or running job.
- `POST /api/v1/jobs/{job_id}/retry`: Reset a failed/dead-letter job back to pending.
- `GET /api/v1/jobs/registered-tasks`: List all registered task identifiers.

### Queues & Metrics

- `GET /api/v1/queues`: Breakdown of job counts across states for every queue.
- `GET /api/v1/workers`: List active worker instances with concurrency and throughput metrics.
- `GET /health` or `GET /api/v1/health`: System health check endpoint.

### Schedules

- `POST /api/v1/schedules`: Define a recurring interval or cron schedule.
- `GET /api/v1/schedules`: List active recurring schedules.
- `DELETE /api/v1/schedules/{schedule_id}`: Remove a recurring schedule.

---

## Testing

Run the automated test suite with pytest:

```powershell
.venv\Scripts\pytest -v
```

The test suite covers:
- Core task registry registration and context detection.
- Worker priority claiming, execution, timeouts, retries, and dead-letter transitions.
- Scheduler delayed job promotions and cron calculations.
- API endpoints for job management, queue statistics, and worker heartbeats.
- CLI commands via Click's `CliRunner`.
