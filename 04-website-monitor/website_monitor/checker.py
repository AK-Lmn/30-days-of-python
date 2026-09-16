import asyncio
from datetime import datetime, timezone
import socket
import ssl
import time
from typing import Optional
from urllib.parse import urlparse

import httpx

from website_monitor.config import DEFAULT_USER_AGENT
from website_monitor.models import MonitorTarget, CheckResult


def parse_hostname(url: str) -> Optional[str]:
    try:
        parsed = urlparse(url)
        return parsed.hostname
    except Exception:
        return None


def check_ssl_expiry(hostname: str, port: int = 443, timeout: float = 5.0) -> Optional[int]:
    try:
        context = ssl.create_default_context()
        with socket.create_connection((hostname, port), timeout=timeout) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                if not cert:
                    return None
                not_after_str = cert.get("notAfter")
                if not not_after_str:
                    return None
                expire_date = datetime.strptime(not_after_str, "%b %d %H:%M:%S %Y %Z").replace(
                    tzinfo=timezone.utc
                )
                now = datetime.now(timezone.utc)
                diff = expire_date - now
                return max(0, diff.days)
    except Exception:
        return None


def check_target(target: MonitorTarget, client: Optional[httpx.Client] = None) -> CheckResult:
    start_time = time.perf_counter()
    headers = dict(target.headers)
    if "User-Agent" not in headers and "user-agent" not in headers:
        headers["User-Agent"] = DEFAULT_USER_AGENT

    ssl_days: Optional[int] = None
    if target.url.startswith("https://"):
        hostname = parse_hostname(target.url)
        if hostname:
            ssl_days = check_ssl_expiry(hostname, timeout=min(target.timeout_seconds, 5.0))

    def _execute(c: httpx.Client) -> CheckResult:
        nonlocal ssl_days
        try:
            req_kwargs = {
                "method": target.method,
                "url": target.url,
                "headers": headers,
                "timeout": target.timeout_seconds,
                "follow_redirects": True,
            }
            if target.request_body:
                req_kwargs["content"] = target.request_body.encode("utf-8")

            response = c.request(**req_kwargs)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            status_matches = (
                response.status_code == target.expected_status
                or (target.expected_status == 200 and 200 <= response.status_code < 300)
            )

            is_up = status_matches
            error_message = None

            if not status_matches:
                error_message = f"Expected status {target.expected_status}, received {response.status_code}"
            elif target.keyword and target.keyword not in response.text:
                is_up = False
                error_message = f'Keyword "{target.keyword}" missing from response'

            return CheckResult(
                target_id=target.id or 0,
                target_name=target.name,
                target_url=target.url,
                is_up=is_up,
                status_code=response.status_code,
                response_time_ms=elapsed_ms,
                error_message=error_message,
                ssl_days_left=ssl_days,
            )
        except httpx.TimeoutException:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return CheckResult(
                target_id=target.id or 0,
                target_name=target.name,
                target_url=target.url,
                is_up=False,
                status_code=None,
                response_time_ms=elapsed_ms,
                error_message=f"Request timed out after {target.timeout_seconds}s",
                ssl_days_left=ssl_days,
            )
        except httpx.ConnectError as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return CheckResult(
                target_id=target.id or 0,
                target_name=target.name,
                target_url=target.url,
                is_up=False,
                status_code=None,
                response_time_ms=elapsed_ms,
                error_message=f"Connection failed: {str(e)}",
                ssl_days_left=ssl_days,
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return CheckResult(
                target_id=target.id or 0,
                target_name=target.name,
                target_url=target.url,
                is_up=False,
                status_code=None,
                response_time_ms=elapsed_ms,
                error_message=str(e),
                ssl_days_left=ssl_days,
            )

    if client is not None:
        return _execute(client)
    with httpx.Client() as standalone_client:
        return _execute(standalone_client)


async def async_check_target(
    target: MonitorTarget, client: Optional[httpx.AsyncClient] = None
) -> CheckResult:
    start_time = time.perf_counter()
    headers = dict(target.headers)
    if "User-Agent" not in headers and "user-agent" not in headers:
        headers["User-Agent"] = DEFAULT_USER_AGENT

    ssl_days: Optional[int] = None
    if target.url.startswith("https://"):
        hostname = parse_hostname(target.url)
        if hostname:
            ssl_days = await asyncio.to_thread(
                check_ssl_expiry, hostname, 443, min(target.timeout_seconds, 5.0)
            )

    async def _execute(c: httpx.AsyncClient) -> CheckResult:
        nonlocal ssl_days
        try:
            req_kwargs = {
                "method": target.method,
                "url": target.url,
                "headers": headers,
                "timeout": target.timeout_seconds,
                "follow_redirects": True,
            }
            if target.request_body:
                req_kwargs["content"] = target.request_body.encode("utf-8")

            response = await c.request(**req_kwargs)
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            status_matches = (
                response.status_code == target.expected_status
                or (target.expected_status == 200 and 200 <= response.status_code < 300)
            )

            is_up = status_matches
            error_message = None

            if not status_matches:
                error_message = f"Expected status {target.expected_status}, received {response.status_code}"
            elif target.keyword and target.keyword not in response.text:
                is_up = False
                error_message = f'Keyword "{target.keyword}" missing from response'

            return CheckResult(
                target_id=target.id or 0,
                target_name=target.name,
                target_url=target.url,
                is_up=is_up,
                status_code=response.status_code,
                response_time_ms=elapsed_ms,
                error_message=error_message,
                ssl_days_left=ssl_days,
            )
        except httpx.TimeoutException:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return CheckResult(
                target_id=target.id or 0,
                target_name=target.name,
                target_url=target.url,
                is_up=False,
                status_code=None,
                response_time_ms=elapsed_ms,
                error_message=f"Request timed out after {target.timeout_seconds}s",
                ssl_days_left=ssl_days,
            )
        except httpx.ConnectError as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return CheckResult(
                target_id=target.id or 0,
                target_name=target.name,
                target_url=target.url,
                is_up=False,
                status_code=None,
                response_time_ms=elapsed_ms,
                error_message=f"Connection failed: {str(e)}",
                ssl_days_left=ssl_days,
            )
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return CheckResult(
                target_id=target.id or 0,
                target_name=target.name,
                target_url=target.url,
                is_up=False,
                status_code=None,
                response_time_ms=elapsed_ms,
                error_message=str(e),
                ssl_days_left=ssl_days,
            )

    if client is not None:
        return await _execute(client)
    async with httpx.AsyncClient() as standalone_client:
        return await _execute(standalone_client)
