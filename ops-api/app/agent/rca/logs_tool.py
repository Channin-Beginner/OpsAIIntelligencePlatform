"""Loki LogQL 查询 + 本地日志降级（阶段三 3.B.2）。"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

from app.agent.rca.types import evidence_item
from app.config import get_settings

ALLOWED_LOG_TEMPLATES: dict[str, str] = {
    "service_logs": '{{service="{service}"}}',
    "error_logs": '{{service="{service}"}} |= "error"',
    "warn_or_error": '{{service="{service}"}} |~ "(?i)(error|exception|traceback)"',
    "request_id": '{{service="{service}"}} | json | request_id="{request_id}"',
    "status_500": '{{service="{service}"}} |~ " 500 "',
}

SERVICE_LOG_FILES: dict[str, str] = {
    "ecom-api-admin": "admin.log",
    "ecom-api-portal": "portal.log",
}


def _validate_label_value(value: str, field: str) -> None:
    if not value or any(ch in value for ch in ('"', "\\", "\n", "\r", "{", "}")):
        raise ValueError(f"{field} 参数非法")


def _build_logql(
    query_id: str,
    *,
    service: str,
    request_id: str | None = None,
) -> str:
    template = ALLOWED_LOG_TEMPLATES.get(query_id)
    if template is None:
        allowed = ", ".join(sorted(ALLOWED_LOG_TEMPLATES))
        raise ValueError(f"不支持的 query_id={query_id!r}，允许: {allowed}")
    _validate_label_value(service, "service")
    if query_id == "request_id":
        if not request_id:
            raise ValueError("request_id 查询必须提供 request_id 参数")
        _validate_label_value(request_id, "request_id")
        return template.format(service=service, request_id=request_id)
    return template.format(service=service)


def _ns_timestamp(dt: datetime) -> str:
    aware = dt.astimezone(timezone.utc)
    return str(int(aware.timestamp() * 1_000_000_000))


def _query_loki(
    logql: str,
    *,
    start: datetime,
    end: datetime,
    limit: int,
    timeout: float,
) -> dict[str, Any] | None:
    settings = get_settings()
    base = settings.loki_base_url.rstrip("/")
    url = f"{base}/loki/api/v1/query_range"
    params = {
        "query": logql,
        "start": _ns_timestamp(start),
        "end": _ns_timestamp(end),
        "limit": str(limit),
        "direction": "backward",
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, params=params)
            if response.status_code >= 500:
                return None
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError:
        return None


def _parse_loki_streams(body: dict[str, Any]) -> list[dict[str, Any]]:
    streams = body.get("data", {}).get("result", [])
    lines: list[dict[str, Any]] = []
    for stream in streams:
        labels = stream.get("stream", {})
        for ts, line in stream.get("values", []):
            lines.append({"timestamp": ts, "labels": labels, "line": line})
    lines.sort(key=lambda item: item["timestamp"], reverse=True)
    return lines


def _read_local_log_file(
    service: str,
    *,
    keyword: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    settings = get_settings()
    filename = SERVICE_LOG_FILES.get(service)
    if not filename:
        return []

    log_path = Path(settings.ecom_log_dir) / filename
    if not log_path.is_file():
        return []

    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    matched: list[dict[str, Any]] = []
    pattern = re.compile(keyword, re.IGNORECASE) if keyword else None
    for line in reversed(text.splitlines()):
        if pattern and not pattern.search(line):
            continue
        matched.append(
            {
                "timestamp": None,
                "labels": {"service": service, "source": "local_file"},
                "line": line,
            }
        )
        if len(matched) >= limit:
            break
    return matched


def query_logs(
    query_id: str,
    *,
    service: str = "ecom-api-portal",
    request_id: str | None = None,
    lookback_minutes: int = 30,
    limit: int = 50,
    timeout: float | None = None,
) -> dict[str, Any]:
    """
    优先 Loki LogQL；不可用时降级读取 EcomAI 本地日志文件。
    """
    settings = get_settings()
    logql = _build_logql(query_id, service=service, request_id=request_id)
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=lookback_minutes)
    client_timeout = timeout or settings.observability_http_timeout

    body = _query_loki(
        logql,
        start=start,
        end=end,
        limit=limit,
        timeout=client_timeout,
    )

    if body and body.get("status") == "success":
        lines = _parse_loki_streams(body)
        summary = f"Loki 返回 {len(lines)} 条日志"
        if lines:
            preview = lines[0]["line"][:200]
            summary += f"；最近: {preview}"
        return evidence_item(
            type="log",
            source="loki",
            summary=summary,
            query=logql,
            detail={"lines": lines[:limit], "backend": "loki"},
        )

    keyword = None
    if query_id in ("error_logs", "warn_or_error", "status_500"):
        keyword = r"error|exception|traceback| 500 "
    elif query_id == "request_id" and request_id:
        keyword = re.escape(request_id)

    local_lines = _read_local_log_file(service, keyword=keyword, limit=limit)
    if local_lines:
        preview = local_lines[0]["line"][:200]
        return evidence_item(
            type="log",
            source="local_file",
            summary=f"本地日志 {len(local_lines)} 条（Loki 不可用）；最近: {preview}",
            query=logql,
            detail={
                "lines": local_lines,
                "backend": "local_file",
                "path": str(Path(settings.ecom_log_dir) / SERVICE_LOG_FILES.get(service, "")),
            },
        )

    return evidence_item(
        type="log",
        source="loki",
        summary="Loki 与本地日志均无匹配结果",
        query=logql,
        detail={"backend": "none", "lines": []},
    )


def list_allowed_log_queries() -> list[dict[str, str]]:
    return [
        {"query_id": key, "description": _LOG_QUERY_DESCRIPTIONS.get(key, key)}
        for key in sorted(ALLOWED_LOG_TEMPLATES)
    ]


_LOG_QUERY_DESCRIPTIONS = {
    "service_logs": "按 service 标签拉取日志",
    "error_logs": "含 error 关键字的日志",
    "warn_or_error": "error/exception/traceback 日志",
    "request_id": "按 request_id JSON 字段过滤",
    "status_500": "HTTP 500 访问日志",
}
