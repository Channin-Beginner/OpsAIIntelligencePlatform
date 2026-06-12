"""Tempo / Jaeger 链路查询（阶段三 3.B.3）。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import httpx

from app.agent.rca.types import evidence_item
from app.config import get_settings

TraceBackend = Literal["tempo", "jaeger"]


def _validate_trace_id(trace_id: str) -> None:
    cleaned = trace_id.strip()
    if not cleaned or len(cleaned) > 128:
        raise ValueError("trace_id 非法")
    if any(ch in cleaned for ch in ('"', "\\", "\n", "\r", " ")):
        raise ValueError("trace_id 非法")


def _validate_service_name(service: str) -> None:
    if not service or any(ch in service for ch in ('"', "\\", "\n", "\r")):
        raise ValueError("service 参数非法")


def _iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fetch_trace_tempo(trace_id: str, timeout: float) -> dict[str, Any] | None:
    settings = get_settings()
    url = f"{settings.tempo_base_url.rstrip('/')}/api/traces/{trace_id}"
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
            if response.status_code == 404:
                return {"status": "not_found"}
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        return {"status": "error", "error": str(exc)}


def _fetch_trace_jaeger(trace_id: str, timeout: float) -> dict[str, Any] | None:
    settings = get_settings()
    url = f"{settings.jaeger_base_url.rstrip('/')}/api/traces/{trace_id}"
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
            if response.status_code == 404:
                return {"status": "not_found"}
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        return {"status": "error", "error": str(exc)}


def _search_traces_tempo(
    service: str,
    *,
    start: datetime,
    end: datetime,
    limit: int,
    timeout: float,
) -> dict[str, Any] | None:
    settings = get_settings()
    url = f"{settings.tempo_base_url.rstrip('/')}/api/search"
    params = {
        "tags": f"service.name={service}",
        "start": str(int(start.timestamp())),
        "end": str(int(end.timestamp())),
        "limit": str(limit),
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        return {"status": "error", "error": str(exc)}


def _search_traces_jaeger(
    service: str,
    *,
    start: datetime,
    end: datetime,
    limit: int,
    timeout: float,
) -> dict[str, Any] | None:
    settings = get_settings()
    url = f"{settings.jaeger_base_url.rstrip('/')}/api/traces"
    params = {
        "service": service,
        "start": _iso_utc(start),
        "end": _iso_utc(end),
        "limit": str(limit),
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        return {"status": "error", "error": str(exc)}


def _summarize_trace_payload(body: dict[str, Any], backend: TraceBackend) -> str:
    if body.get("status") == "not_found":
        return "未找到 trace"
    if body.get("status") == "error":
        return f"查询失败: {body.get('error', 'unknown')}"

    if backend == "tempo":
        batches = body.get("batches", [])
        if not batches:
            return "空 trace"
        spans = sum(len(batch.get("scopeSpans", [])) for batch in batches)
        return f"Tempo trace 含 {len(batches)} batch / ~{spans} scopeSpan 组"

    data = body.get("data", [])
    if not data:
        return "空 trace"
    trace = data[0]
    spans = trace.get("spans", [])
    processes = trace.get("processes", {})
    return f"Jaeger trace 含 {len(spans)} spans，{len(processes)} processes"


def get_trace_by_id(
    trace_id: str,
    *,
    backend: TraceBackend | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """按 trace_id 查询完整链路。"""
    settings = get_settings()
    _validate_trace_id(trace_id)
    resolved_backend: TraceBackend = backend or settings.trace_backend  # type: ignore[assignment]
    client_timeout = timeout or settings.observability_http_timeout

    if resolved_backend == "jaeger":
        body = _fetch_trace_jaeger(trace_id, client_timeout)
        source = "jaeger"
    else:
        body = _fetch_trace_tempo(trace_id, client_timeout)
        source = "tempo"

    if body is None:
        body = {"status": "error", "error": "no response"}

    return evidence_item(
        type="trace",
        source=source,
        summary=_summarize_trace_payload(body, resolved_backend),
        query=f"trace_id={trace_id}",
        detail={"trace_id": trace_id, "backend": resolved_backend, "payload": body},
    )


def search_traces(
    service: str,
    *,
    lookback_minutes: int = 30,
    limit: int = 20,
    backend: TraceBackend | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """按服务名与时间窗搜索 trace 列表。"""
    settings = get_settings()
    _validate_service_name(service)
    resolved_backend: TraceBackend = backend or settings.trace_backend  # type: ignore[assignment]
    client_timeout = timeout or settings.observability_http_timeout
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=lookback_minutes)

    if resolved_backend == "jaeger":
        body = _search_traces_jaeger(
            service, start=start, end=end, limit=limit, timeout=client_timeout
        )
        source = "jaeger"
    else:
        body = _search_traces_tempo(
            service, start=start, end=end, limit=limit, timeout=client_timeout
        )
        source = "tempo"

    if body is None:
        body = {"status": "error", "error": "no response"}

    traces = body.get("traces", [])
    if resolved_backend == "jaeger" and "data" in body:
        traces = body.get("data", [])

    summary = f"{source} 搜索 {service} 返回 {len(traces)} 条 trace"
    return evidence_item(
        type="trace",
        source=source,
        summary=summary,
        query=f'service="{service}" lookback={lookback_minutes}m',
        detail={
            "service": service,
            "backend": resolved_backend,
            "traces": traces[:limit],
            "raw": body,
        },
    )
