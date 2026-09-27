import asyncio
from typing import Any

from taskforge.core.executor import ExecutionContext
from taskforge.core.registry import task


@task(name="send_email", timeout_seconds=30.0, default_max_retries=3)
async def send_email(
    to: str,
    subject: str,
    body: str = "",
    fail: bool = False,
    context: ExecutionContext | None = None,
) -> dict[str, Any]:
    if context:
        await context.report_progress(20.0, "Resolving DNS & MX records")
    await asyncio.sleep(0.05)

    if context:
        await context.report_progress(50.0, "Connecting to SMTP server")
    await asyncio.sleep(0.05)

    if fail:
        raise ValueError(f"SMTP error: failed to deliver email to {to}")

    if context:
        await context.report_progress(80.0, "Sending MIME payload")
    await asyncio.sleep(0.05)

    if context:
        await context.report_progress(100.0, "Email delivered successfully")

    return {
        "status": "delivered",
        "to": to,
        "subject": subject,
        "bytes_sent": len(body.encode("utf-8")),
    }


@task(name="generate_report", timeout_seconds=60.0, default_max_retries=2)
async def generate_report(
    report_type: str = "executive_summary",
    records_count: int = 500,
    context: ExecutionContext | None = None,
) -> dict[str, Any]:
    steps = 4
    for step in range(1, steps + 1):
        pct = (step / steps) * 100.0
        if context:
            await context.report_progress(
                pct, f"Aggregating dataset chunk {step}/{steps}"
            )
        await asyncio.sleep(0.05)

    return {
        "report_type": report_type,
        "records_processed": records_count,
        "metrics": {
            "p50_latency_ms": 42.5,
            "p99_latency_ms": 118.2,
            "error_rate_pct": 0.04,
        },
    }


@task(name="resize_image", timeout_seconds=30.0, default_max_retries=3)
async def resize_image(
    source_url: str,
    target_width: int = 800,
    target_height: int = 600,
    format: str = "webp",
    context: ExecutionContext | None = None,
) -> dict[str, Any]:
    if context:
        await context.report_progress(30.0, f"Downloading image from {source_url}")
    await asyncio.sleep(0.05)

    if context:
        await context.report_progress(70.0, f"Resampling to {target_width}x{target_height}")
    await asyncio.sleep(0.05)

    if context:
        await context.report_progress(100.0, f"Encoded to {format}")

    return {
        "source_url": source_url,
        "output_width": target_width,
        "output_height": target_height,
        "format": format,
        "optimized_size_bytes": 48210,
    }


@task(name="data_export", timeout_seconds=45.0, default_max_retries=2)
async def data_export(
    collection: str = "users",
    file_format: str = "csv",
    context: ExecutionContext | None = None,
) -> dict[str, Any]:
    if context:
        await context.report_progress(20.0, f"Querying collection {collection}")
    await asyncio.sleep(0.05)

    if context:
        await context.report_progress(60.0, f"Formatting stream as {file_format}")
    await asyncio.sleep(0.05)

    if context:
        await context.report_progress(100.0, "Export package ready")

    return {
        "collection": collection,
        "format": file_format,
        "exported_rows": 1250,
        "download_url": f"https://cdn.example.internal/exports/{collection}.{file_format}",
    }


@task(name="cleanup_expired_sessions", timeout_seconds=20.0, default_max_retries=1)
async def cleanup_expired_sessions(
    retention_days: int = 30,
    context: ExecutionContext | None = None,
) -> dict[str, Any]:
    if context:
        await context.report_progress(50.0, "Scanning expired session tokens")
    await asyncio.sleep(0.05)

    if context:
        await context.report_progress(100.0, "Purged expired records")

    return {
        "retention_days": retention_days,
        "deleted_count": 84,
    }


@task(name="failing_task", timeout_seconds=10.0, default_max_retries=2)
async def failing_task(
    message: str = "intentional task failure",
    context: ExecutionContext | None = None,
) -> None:
    if context:
        await context.report_progress(10.0, "Starting failing task")
    raise RuntimeError(message)


@task(name="slow_task", timeout_seconds=5.0, default_max_retries=1)
async def slow_task(
    duration: float = 2.0,
    context: ExecutionContext | None = None,
) -> dict[str, Any]:
    step_duration = duration / 5.0
    for i in range(1, 6):
        await asyncio.sleep(step_duration)
        if context:
            await context.report_progress(i * 20.0, f"Step {i}/5 completed")
    return {"duration": duration, "status": "completed"}
