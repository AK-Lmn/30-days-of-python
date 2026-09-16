from datetime import datetime, timezone
import os
from pathlib import Path
import re
import time
from typing import Any, Dict, Optional
import httpx
from api_cli.config import USER_AGENT
from api_cli.db import add_history_entry, get_active_environment, get_environment
from api_cli.models import Environment, HistoryEntry, RequestConfig, ResponseResult

VARIABLE_PATTERN = re.compile(r"\{\{([a-zA-Z0-9_\-\.]+)\}\}")


def interpolate_string(text: str, variables: Dict[str, str]) -> str:
    if not text:
        return text

    def replace_match(match: re.Match) -> str:
        var_name = match.group(1)
        if var_name in variables:
            return str(variables[var_name])
        env_val = os.getenv(var_name)
        if env_val is not None:
            return env_val
        return match.group(0)

    return VARIABLE_PATTERN.sub(replace_match, text)


def build_variable_map(env: Optional[Environment]) -> Dict[str, str]:
    var_map: Dict[str, str] = {}
    if env:
        if env.base_url:
            var_map["base_url"] = env.base_url
        var_map.update(env.variables)
    return var_map


def resolve_request_config(config: RequestConfig, env: Optional[Environment] = None) -> RequestConfig:
    var_map = build_variable_map(env)

    raw_url = interpolate_string(config.url, var_map)
    if env and env.base_url and not (raw_url.startswith("http://") or raw_url.startswith("https://")):
        base = env.base_url.rstrip("/")
        path = raw_url.lstrip("/")
        final_url = f"{base}/{path}"
    else:
        final_url = raw_url

    headers: Dict[str, str] = {}
    if env:
        for k, v in env.headers.items():
            headers[interpolate_string(k, var_map)] = interpolate_string(v, var_map)

    for k, v in config.headers.items():
        headers[interpolate_string(k, var_map)] = interpolate_string(v, var_map)

    if not any(k.lower() == "user-agent" for k in headers):
        headers["User-Agent"] = USER_AGENT

    query_params: Dict[str, str] = {}
    for k, v in config.query_params.items():
        query_params[interpolate_string(k, var_map)] = interpolate_string(v, var_map)

    resolved_body: Optional[str] = None
    if config.body:
        resolved_body = interpolate_string(config.body, var_map)

    return RequestConfig(
        method=config.method.upper(),
        url=final_url,
        headers=headers,
        query_params=query_params,
        body=resolved_body,
        timeout=config.timeout,
        verify_ssl=config.verify_ssl,
        follow_redirects=config.follow_redirects,
    )


def execute_request(
    config: RequestConfig,
    env_name: Optional[str] = None,
    save_to_history: bool = True,
    db_path: Optional[Path] = None,
    client: Optional[httpx.Client] = None,
) -> ResponseResult:
    target_env_name = env_name if env_name is not None else get_active_environment(db_path)
    env = get_environment(target_env_name, db_path) if target_env_name else None
    resolved = resolve_request_config(config, env)

    timestamp = datetime.now(timezone.utc).isoformat()
    start_time = time.perf_counter()

    headers_dict = dict(resolved.headers)
    body_data = resolved.body.encode("utf-8") if resolved.body is not None else None

    own_client = client is None
    http_client = client or httpx.Client(
        verify=resolved.verify_ssl,
        follow_redirects=resolved.follow_redirects,
        timeout=resolved.timeout,
    )

    try:
        response = http_client.request(
            method=resolved.method,
            url=resolved.url,
            params=resolved.query_params if resolved.query_params else None,
            headers=headers_dict,
            content=body_data,
        )
        latency_ms = (time.perf_counter() - start_time) * 1000
        resp_headers = dict(response.headers)
        content_type = resp_headers.get("content-type", "")
        body_text = response.text
        size_bytes = len(response.content)

        result = ResponseResult(
            status_code=response.status_code,
            reason_phrase=response.reason_phrase,
            headers=resp_headers,
            body=body_text,
            latency_ms=latency_ms,
            content_type=content_type,
            size_bytes=size_bytes,
            timestamp=timestamp,
        )
    except httpx.TimeoutException as exc:
        latency_ms = (time.perf_counter() - start_time) * 1000
        result = ResponseResult(
            status_code=504,
            reason_phrase="Gateway Timeout",
            headers={},
            body=f"Request timed out after {resolved.timeout} seconds: {str(exc)}",
            latency_ms=latency_ms,
            content_type="text/plain",
            size_bytes=0,
            timestamp=timestamp,
        )
    except httpx.RequestError as exc:
        latency_ms = (time.perf_counter() - start_time) * 1000
        result = ResponseResult(
            status_code=0,
            reason_phrase="Request Error",
            headers={},
            body=f"HTTP connection failed: {str(exc)}",
            latency_ms=latency_ms,
            content_type="text/plain",
            size_bytes=0,
            timestamp=timestamp,
        )
    finally:
        if own_client:
            http_client.close()

    if save_to_history:
        history_entry = HistoryEntry(
            timestamp=timestamp,
            method=resolved.method,
            url=resolved.url,
            status_code=result.status_code,
            latency_ms=result.latency_ms,
            request_headers=resolved.headers,
            request_body=resolved.body,
            response_headers=result.headers,
            response_body=result.body,
            size_bytes=result.size_bytes,
        )
        add_history_entry(history_entry, db_path)

    return result
