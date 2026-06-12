"""Prometheus PromQL 白名单查询（阶段三 3.B.1）。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.agent.rca.types import evidence_item
from app.config import get_settings

# 仅允许预置模板，禁止任意 PromQL 注入
ALLOWED_QUERY_TEMPLATES: dict[str, str] = {
    "service_up": 'up{{job=~"{job}"}}',
    "http_qps": (
        'sum(rate(http_requests_total{{job=~"{job}"}}[5m])) by (job)'
    ),
    "error_rate": (
        'sum(rate(http_requests_total{{job=~"{job}", status=~"5.."}}[5m])) by (job)'
        " / "
        'sum(rate(http_requests_total{{job=~"{job}"}}[5m])) by (job)'
    ),
    "p95_latency": (
        "histogram_quantile(0.95, "
        'sum(rate(http_request_duration_highr_seconds_bucket{{job=~"{job}"}}[5m])) by (le, job)'
        ")"
    ),
    "otel_collector_up": 'up{{job="otel-collector"}}',
}

DEFAULT_JOB_PATTERN = "ecom-api-.*"


def _build_promql(query_id: str, *, job: str) -> str:
    template = ALLOWED_QUERY_TEMPLATES.get(query_id)
    if template is None:
        allowed = ", ".join(sorted(ALLOWED_QUERY_TEMPLATES))
        raise ValueError(f"不支持的 query_id={query_id!r}，允许: {allowed}")
    if not job or any(ch in job for ch in ('"', "\\", "\n", "\r")):
        raise ValueError("job 参数非法")
    return template.format(job=job)


def _summarize_vector_result(data: dict[str, Any]) -> str:
    result = data.get("data", {}).get("result", [])
    if not result:
        return "无数据点"
    parts: list[str] = []
    for series in result[:5]:
        metric = series.get("metric", {})
        label = metric.get("job") or metric.get("__name__") or "series"
        value = series.get("value")
        if isinstance(value, list) and len(value) >= 2:
            parts.append(f"{label}={value[1]}")
        else:
            parts.append(str(label))
    suffix = f" 等 {len(result)} 条" if len(result) > 5 else ""
    return "; ".join(parts) + suffix


def query_metrics(
    query_id: str,
    *,
    job: str = DEFAULT_JOB_PATTERN,
    at_time: datetime | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """
    对白名单 PromQL 查询 Prometheus HTTP API，返回证据结构。

    :param query_id: 预置查询 ID（见 ALLOWED_QUERY_TEMPLATES）
    :param job: Prometheus job 正则，默认 ecom-api-.*
    """
    settings = get_settings()
    promql = _build_promql(query_id, job=job)
    params: dict[str, str] = {"query": promql}
    if at_time is not None:
        ts = at_time.astimezone(timezone.utc).timestamp()
        params["time"] = str(int(ts))

    url = f"{settings.prometheus_base_url.rstrip('/')}/api/v1/query"
    client_timeout = timeout or settings.observability_http_timeout

    try:
        with httpx.Client(timeout=client_timeout) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            body = response.json()
    except httpx.HTTPError as exc:
        return evidence_item(
            type="metric",
            source="prometheus",
            summary=f"Prometheus 查询失败: {exc}",
            query=promql,
            detail={"query_id": query_id, "error": str(exc)},
        )

    status = body.get("status", "unknown")
    if status != "success":
        return evidence_item(
            type="metric",
            source="prometheus",
            summary=f"Prometheus 返回非 success: {status}",
            query=promql,
            detail=body,
        )

    summary = _summarize_vector_result(body)
    return evidence_item(
        type="metric",
        source="prometheus",
        summary=summary,
        query=promql,
        detail={
            "query_id": query_id,
            "job": job,
            "result_type": body.get("data", {}).get("resultType"),
            "result": body.get("data", {}).get("result", []),
        },
    )


def list_allowed_metric_queries() -> list[dict[str, str]]:
    """供 RCA Agent / 管理台展示可用指标查询。"""
    return [
        {"query_id": key, "description": _QUERY_DESCRIPTIONS.get(key, key)}
        for key in sorted(ALLOWED_QUERY_TEMPLATES)
    ]


_QUERY_DESCRIPTIONS = {
    "service_up": "服务存活 up 指标",
    "http_qps": "HTTP QPS（5m rate）",
    "error_rate": "HTTP 5xx 错误率",
    "p95_latency": "HTTP P95 延迟（highr histogram）",
    "otel_collector_up": "OTel Collector 存活",
}
