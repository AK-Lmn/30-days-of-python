import asyncio
from pathlib import Path
import statistics
import time
from typing import Dict, List, Optional
import httpx
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from api_cli.client import resolve_request_config
from api_cli.db import get_active_environment, get_environment
from api_cli.models import BenchmarkStats, RequestConfig


def calculate_stats(latencies: List[float], status_codes: Dict[int, int], total_time_seconds: float) -> BenchmarkStats:
    total_requests = len(latencies)
    if total_requests == 0:
        return BenchmarkStats()

    sorted_latencies = sorted(latencies)
    successful_requests = sum(count for code, count in status_codes.items() if 200 <= code < 400)
    failed_requests = total_requests - successful_requests

    min_lat = sorted_latencies[0]
    max_lat = sorted_latencies[-1]
    avg_lat = statistics.mean(sorted_latencies)
    median_lat = statistics.median(sorted_latencies)

    def percentile(p: float) -> float:
        idx = int(p * len(sorted_latencies))
        idx = min(idx, len(sorted_latencies) - 1)
        return sorted_latencies[idx]

    p95_lat = percentile(0.95)
    p99_lat = percentile(0.99)
    rps = total_requests / total_time_seconds if total_time_seconds > 0 else 0.0

    return BenchmarkStats(
        total_requests=total_requests,
        successful_requests=successful_requests,
        failed_requests=failed_requests,
        total_time_seconds=total_time_seconds,
        requests_per_second=rps,
        min_latency_ms=min_lat,
        avg_latency_ms=avg_lat,
        median_latency_ms=median_lat,
        p95_latency_ms=p95_lat,
        p99_latency_ms=p99_lat,
        max_latency_ms=max_lat,
        status_code_counts=status_codes,
    )


async def _worker(
    semaphore: asyncio.Semaphore,
    client: httpx.AsyncClient,
    config: RequestConfig,
    latencies: List[float],
    status_codes: Dict[int, int],
) -> None:
    body_data = config.body.encode("utf-8") if config.body is not None else None
    async with semaphore:
        start = time.perf_counter()
        try:
            resp = await client.request(
                method=config.method,
                url=config.url,
                params=config.query_params if config.query_params else None,
                headers=config.headers,
                content=body_data,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)
            status_codes[resp.status_code] = status_codes.get(resp.status_code, 0) + 1
        except Exception:
            elapsed_ms = (time.perf_counter() - start) * 1000
            latencies.append(elapsed_ms)
            status_codes[0] = status_codes.get(0, 0) + 1


async def async_run_benchmark(
    config: RequestConfig,
    total_requests: int = 10,
    concurrency: int = 2,
    env_name: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> BenchmarkStats:
    target_env_name = env_name if env_name is not None else get_active_environment(db_path)
    env = get_environment(target_env_name, db_path) if target_env_name else None
    resolved = resolve_request_config(config, env)

    semaphore = asyncio.Semaphore(max(1, concurrency))
    latencies: List[float] = []
    status_codes: Dict[int, int] = {}

    bench_start = time.perf_counter()
    async with httpx.AsyncClient(
        verify=resolved.verify_ssl,
        follow_redirects=resolved.follow_redirects,
        timeout=resolved.timeout,
    ) as client:
        tasks = [
            asyncio.create_task(_worker(semaphore, client, resolved, latencies, status_codes))
            for _ in range(total_requests)
        ]
        await asyncio.gather(*tasks)

    total_time = time.perf_counter() - bench_start
    return calculate_stats(latencies, status_codes, total_time)


def run_benchmark(
    config: RequestConfig,
    total_requests: int = 10,
    concurrency: int = 2,
    env_name: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> BenchmarkStats:
    return asyncio.run(
        async_run_benchmark(
            config=config,
            total_requests=total_requests,
            concurrency=concurrency,
            env_name=env_name,
            db_path=db_path,
        )
    )


def render_benchmark_results(console: Console, stats: BenchmarkStats) -> None:
    summary_table = Table(box=box.ROUNDED, header_style="bold cyan", title="Benchmark Summary")
    summary_table.add_column("Metric", style="bold white")
    summary_table.add_column("Value", style="green")

    summary_table.add_row("Total Requests", str(stats.total_requests))
    summary_table.add_row("Successful Requests", f"[green]{stats.successful_requests}[/]")
    summary_table.add_row("Failed Requests", f"[red]{stats.failed_requests}[/]" if stats.failed_requests else "0")
    summary_table.add_row("Total Duration", f"{stats.total_time_seconds:.3f} s")
    summary_table.add_row("Throughput", f"[bold cyan]{stats.requests_per_second:.2f} req/s[/]")

    lat_table = Table(box=box.ROUNDED, header_style="bold cyan", title="Latency Distribution")
    lat_table.add_column("Percentile / Measure", style="bold white")
    lat_table.add_column("Latency (ms)", style="cyan")

    lat_table.add_row("Fastest (Min)", f"{stats.min_latency_ms:.2f} ms")
    lat_table.add_row("Average (Mean)", f"{stats.avg_latency_ms:.2f} ms")
    lat_table.add_row("50% (Median)", f"{stats.median_latency_ms:.2f} ms")
    lat_table.add_row("95% (p95)", f"{stats.p95_latency_ms:.2f} ms")
    lat_table.add_row("99% (p99)", f"{stats.p99_latency_ms:.2f} ms")
    lat_table.add_row("Slowest (Max)", f"{stats.max_latency_ms:.2f} ms")

    status_table = Table(box=box.ROUNDED, header_style="bold cyan", title="Status Codes")
    status_table.add_column("Status Code", style="bold white")
    status_table.add_column("Count", style="yellow")
    for code, count in sorted(stats.status_code_counts.items()):
        label = str(code) if code > 0 else "Connection Error (0)"
        status_table.add_row(label, str(count))

    console.print(summary_table)
    console.print(lat_table)
    console.print(status_table)
