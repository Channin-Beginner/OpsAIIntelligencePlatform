"""DeepSeek RCA 编排：Incident → 工具证据链 → LLM 根因报告（阶段三 3.C.1）。"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.agent.rca.incident_rag import search_incident_context
from app.agent.rca.llm_client import chat_json
from app.agent.rca.logs_tool import query_logs
from app.agent.rca.metrics_tool import query_metrics
from app.agent.rca.traces_tool import get_trace_by_id, search_traces
from app.agent.rca.types import evidence_item
from app.config import get_settings
from app.models.alert_event import AlertEvent
from app.models.incident import Incident
from app.runbook.recommend import match_runbook_ids, runbooks_for_llm_context

_SYSTEM_PROMPT = """你是企业级 AIOps RCA（根因分析）专家。根据 Incident 信息与已收集的证据链，输出严格 JSON：
{
  "hypothesis": "一句话根因假设（中文）",
  "confidence": 0.0到1.0的小数,
  "suggested_actions": ["建议处置步骤1", "步骤2"],
  "suggested_runbook_ids": [],
  "evidence_refs": [{"index": 0, "reason": "该证据如何支撑结论"}]
}
规则：
1. 结论必须引用 evidence 中的 metric/log/trace/kb，不可编造未提供的观测。
2. confidence 反映证据充分程度；证据不足时降低并说明不确定性。
3. suggested_runbook_ids 必须从 available_runbooks 中选择匹配的 id，无合适则空数组。
4. 只输出 JSON，不要 markdown。"""

_ALERT_METRIC_QUERIES: dict[str, list[str]] = {
    "HighErrorRate": ["error_rate", "http_qps", "service_up"],
    "HighP95Latency": ["p95_latency", "http_qps", "service_up"],
    "EcomApiDown": ["service_up"],
    "AdsRefreshFailed": [],
}

_LOG_QUERY_BY_ALERT: dict[str, str] = {
    "HighErrorRate": "warn_or_error",
    "HighP95Latency": "warn_or_error",
    "EcomApiDown": "service_logs",
    "AdsRefreshFailed": "error_logs",
}


def _job_for_service(service: str | None) -> str:
    if service and service.startswith("ecom-api-"):
        return service
    return "ecom-api-.*"


def _trace_service_name(service: str | None) -> str:
    return service or "ecom-api-portal"


def _compact_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    detail = evidence.get("detail")
    if isinstance(detail, dict):
        trimmed = dict(detail)
        if "lines" in trimmed and isinstance(trimmed["lines"], list):
            trimmed["lines"] = trimmed["lines"][:8]
        if "result" in trimmed and isinstance(trimmed["result"], list):
            trimmed["result"] = trimmed["result"][:5]
        if "payload" in trimmed:
            trimmed.pop("payload", None)
        if "raw" in trimmed:
            trimmed.pop("raw", None)
        if "traces" in trimmed and isinstance(trimmed["traces"], list):
            trimmed["traces"] = trimmed["traces"][:5]
        evidence = {**evidence, "detail": trimmed}
    return evidence


def _collect_metric_evidence(service: str | None, alertname: str | None) -> list[dict[str, Any]]:
    job = _job_for_service(service)
    query_ids = _ALERT_METRIC_QUERIES.get(alertname or "", ["service_up", "http_qps"])
    if not query_ids:
        query_ids = ["service_up"]
    collected: list[dict[str, Any]] = []
    for query_id in query_ids:
        try:
            collected.append(_compact_evidence(query_metrics(query_id, job=job)))
        except ValueError as exc:
            collected.append(
                evidence_item(
                    type="metric",
                    source="prometheus",
                    summary=f"指标查询跳过: {exc}",
                    query=query_id,
                )
            )
    return collected


def _collect_log_evidence(service: str | None, alertname: str | None) -> dict[str, Any]:
    svc = service or "ecom-api-portal"
    query_id = _LOG_QUERY_BY_ALERT.get(alertname or "", "warn_or_error")
    return _compact_evidence(query_logs(query_id, service=svc))


def _collect_trace_evidence(service: str | None) -> dict[str, Any]:
    trace_service = _trace_service_name(service)
    search_evidence = _compact_evidence(search_traces(trace_service, lookback_minutes=30, limit=10))
    traces = (search_evidence.get("detail") or {}).get("traces") or []
    trace_id = None
    if traces:
        first = traces[0]
        if isinstance(first, dict):
            trace_id = (
                first.get("traceID")
                or first.get("trace_id")
                or first.get("id")
            )
    if trace_id:
        return _compact_evidence(get_trace_by_id(str(trace_id)))
    return search_evidence


def _collect_rag_evidence(db: Session, incident: Incident, alert: AlertEvent | None) -> dict[str, Any]:
    parts = [incident.title]
    if incident.description:
        parts.append(incident.description)
    if alert and alert.summary:
        parts.append(alert.summary)
    if alert and alert.alertname:
        parts.append(alert.alertname)
    query = " ".join(parts)
    return search_incident_context(db, query, service=incident.service)


def gather_evidence(
    db: Session,
    incident: Incident,
    *,
    primary_alert: AlertEvent | None = None,
) -> list[dict[str, Any]]:
    """按告警类型收集 metric / log / trace / kb 证据。"""
    alertname = primary_alert.alertname if primary_alert else None
    service = incident.service or (primary_alert.service if primary_alert else None)

    evidence: list[dict[str, Any]] = []
    evidence.extend(_collect_metric_evidence(service, alertname))
    evidence.append(_collect_log_evidence(service, alertname))
    evidence.append(_collect_trace_evidence(service))
    evidence.append(_collect_rag_evidence(db, incident, primary_alert))
    return evidence


def _fallback_analysis(
    db: Session,
    incident: Incident,
    evidence: list[dict[str, Any]],
    *,
    alertname: str | None = None,
) -> dict[str, Any]:
    """无 LLM Key 或调用失败时的规则降级。"""
    kb_hits = [
        e for e in evidence if e.get("type") == "kb" and "未命中" not in e.get("summary", "")
    ]
    error_logs = [
        e
        for e in evidence
        if e.get("type") == "log" and "error" in e.get("summary", "").lower()
    ]
    high_error = [
        e
        for e in evidence
        if e.get("type") == "metric" and "error_rate" in (e.get("query") or "")
    ]

    hypothesis_parts = [f"Incident「{incident.title}」"]
    if error_logs:
        hypothesis_parts.append("日志显示存在 error/5xx 异常")
    if high_error:
        hypothesis_parts.append("指标侧 5xx 错误率升高")
    if kb_hits:
        hypothesis_parts.append("知识库存在相似历史案例")
    hypothesis = "；".join(hypothesis_parts) + "。建议结合 Grafana 与混沌脚本进一步确认。"

    confidence = 0.45
    if kb_hits:
        confidence += 0.2
    if error_logs:
        confidence += 0.15
    if any(e.get("type") == "trace" for e in evidence):
        confidence += 0.1
    confidence = min(confidence, 0.85)

    runbook_ids = match_runbook_ids(
        db,
        service=incident.service,
        alertname=alertname,
    )

    return {
        "hypothesis": hypothesis,
        "confidence": round(confidence, 2),
        "suggested_actions": [
            "在 Grafana 核对对应服务 QPS、错误率、P95",
            "查看 EcomAI 应用日志定位异常路由或下游超时",
            "确认相关混沌注入脚本是否仍在运行",
        ],
        "suggested_runbook_ids": runbook_ids,
        "evidence_refs": [{"index": i, "reason": "自动收集"} for i in range(len(evidence))],
        "model_name": "rule-based-fallback",
    }


def _build_user_prompt(
    incident: Incident,
    primary_alert: AlertEvent | None,
    evidence: list[dict[str, Any]],
    available_runbooks: list[dict[str, Any]],
) -> str:
    alert_block: dict[str, Any] = {}
    if primary_alert:
        alert_block = {
            "alertname": primary_alert.alertname,
            "severity": primary_alert.severity,
            "title": primary_alert.title,
            "summary": primary_alert.summary,
            "fingerprint": primary_alert.fingerprint,
        }
    payload = {
        "incident": {
            "id": incident.id,
            "incident_no": incident.incident_no,
            "title": incident.title,
            "description": incident.description,
            "status": incident.status,
            "severity": incident.severity,
            "service": incident.service,
        },
        "primary_alert": alert_block,
        "evidence": evidence,
        "available_runbooks": available_runbooks,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def analyze_incident(
    db: Session,
    incident: Incident,
    *,
    primary_alert: AlertEvent | None = None,
) -> dict[str, Any]:
    """
    执行完整 RCA 编排，返回 hypothesis / confidence / evidence / actions 等。
    """
    evidence = gather_evidence(db, incident, primary_alert=primary_alert)
    settings = get_settings()
    alertname = primary_alert.alertname if primary_alert else None
    available_runbooks = runbooks_for_llm_context(db)
    rule_runbook_ids = match_runbook_ids(
        db,
        service=incident.service,
        alertname=alertname,
    )

    if not settings.llm_api_key.strip():
        result = _fallback_analysis(db, incident, evidence, alertname=alertname)
        result["evidence"] = evidence
        return result

    user_prompt = _build_user_prompt(incident, primary_alert, evidence, available_runbooks)
    try:
        parsed, model_name = chat_json(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )
    except Exception:
        result = _fallback_analysis(db, incident, evidence, alertname=alertname)
        result["evidence"] = evidence
        result["llm_error"] = True
        return result

    confidence = parsed.get("confidence", 0.5)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))

    suggested_actions = parsed.get("suggested_actions") or []
    if not isinstance(suggested_actions, list):
        suggested_actions = [str(suggested_actions)]

    runbook_ids = parsed.get("suggested_runbook_ids") or []
    if not isinstance(runbook_ids, list):
        runbook_ids = []
    runbook_ids = [int(x) for x in runbook_ids if str(x).isdigit()]
    if not runbook_ids and rule_runbook_ids:
        runbook_ids = rule_runbook_ids

    return {
        "hypothesis": str(parsed.get("hypothesis") or "未能生成根因假设"),
        "confidence": round(confidence, 3),
        "suggested_actions": [str(a) for a in suggested_actions],
        "suggested_runbook_ids": runbook_ids,
        "evidence_refs": parsed.get("evidence_refs") or [],
        "evidence": evidence,
        "model_name": model_name,
    }
