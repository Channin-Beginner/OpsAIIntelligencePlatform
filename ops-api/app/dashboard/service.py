"""运维大屏 ADS 聚合与 8 模块数据（阶段五 5.5 / 5.7）。"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from math import isfinite
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.ads import AdsAgentQuality, AdsAlertDaily, AdsMttrDaily
from app.models.alert_event import AlertEvent
from app.models.incident import Incident
from app.models.incident_feedback import IncidentFeedback
from app.models.kb_article import KbArticle
from app.models.rca_result import RcaResult
from app.models.runbook import RunbookExecution
from app.runbook.service import get_adoption_stats
from app.schemas.common import DashboardOverviewSchema

OPEN_STATUSES = ("open", "acknowledged", "investigating", "mitigated")


def _today() -> date:
    return datetime.now().date()


def _decimal_rate(num: int, den: int) -> Decimal | None:
    if den <= 0:
        return None
    return Decimal(str(round(num / den, 4)))


def refresh_ads_tables(db: Session, *, days: int = 90) -> dict[str, int]:
    """从 ODS 表刷新 ads_* 聚合（阶段五 5.6）。"""
    end = _today()
    start = end - timedelta(days=days)
    updated = {"alert": 0, "mttr": 0, "agent": 0}

    day = start
    while day <= end:
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day + timedelta(days=1), datetime.min.time())

        alerts = list(
            db.scalars(
                select(AlertEvent).where(
                    AlertEvent.created_at >= day_start,
                    AlertEvent.created_at < day_end,
                )
            ).all()
        )
        raw_count = len(alerts)
        deduped = len({a.fingerprint for a in alerts})
        am_count = sum(1 for a in alerts if a.source == "alertmanager")
        gf_count = sum(1 for a in alerts if a.source == "grafana")

        alert_row = db.get(AdsAlertDaily, day)
        if alert_row is None:
            alert_row = AdsAlertDaily(stat_date=day)
            db.add(alert_row)
        alert_row.raw_count = raw_count
        alert_row.deduped_count = deduped
        alert_row.alertmanager_count = am_count
        alert_row.grafana_count = gf_count
        updated["alert"] += 1

        resolved = list(
            db.scalars(
                select(Incident).where(
                    Incident.resolved_at.isnot(None),
                    Incident.resolved_at >= day_start,
                    Incident.resolved_at < day_end,
                )
            ).all()
        )
        mttr_values: list[float] = []
        for inc in resolved:
            if inc.resolved_at and inc.created_at:
                delta = (inc.resolved_at - inc.created_at).total_seconds() / 60.0
                if delta >= 0:
                    mttr_values.append(delta)

        mttr_row = db.get(AdsMttrDaily, day)
        if mttr_row is None:
            mttr_row = AdsMttrDaily(stat_date=day)
            db.add(mttr_row)
        mttr_row.incident_count = len(resolved)
        if mttr_values:
            mttr_values.sort()
            mttr_row.mttr_avg_minutes = Decimal(str(round(sum(mttr_values) / len(mttr_values), 2)))
            mid = mttr_values[len(mttr_values) // 2]
            mttr_row.mttr_p50_minutes = Decimal(str(round(mid, 2)))
        else:
            mttr_row.mttr_avg_minutes = None
            mttr_row.mttr_p50_minutes = None
        updated["mttr"] += 1

        rca_total = int(
            db.scalar(
                select(func.count())
                .select_from(RcaResult)
                .where(
                    RcaResult.status == "completed",
                    RcaResult.completed_at >= day_start,
                    RcaResult.completed_at < day_end,
                )
            )
            or 0
        )
        rca_accept = int(
            db.scalar(
                select(func.count())
                .select_from(IncidentFeedback)
                .where(
                    IncidentFeedback.verdict == "accept",
                    IncidentFeedback.created_at >= day_start,
                    IncidentFeedback.created_at < day_end,
                )
            )
            or 0
        )
        rb_total = int(
            db.scalar(
                select(func.count())
                .select_from(RunbookExecution)
                .where(
                    RunbookExecution.created_at >= day_start,
                    RunbookExecution.created_at < day_end,
                )
            )
            or 0
        )
        rb_success = int(
            db.scalar(
                select(func.count())
                .select_from(RunbookExecution)
                .where(
                    RunbookExecution.status == "completed",
                    RunbookExecution.created_at >= day_start,
                    RunbookExecution.created_at < day_end,
                )
            )
            or 0
        )
        kb_pub = int(
            db.scalar(
                select(func.count())
                .select_from(KbArticle)
                .where(
                    KbArticle.status == "published",
                    KbArticle.updated_at >= day_start,
                    KbArticle.updated_at < day_end,
                )
            )
            or 0
        )
        open_count = int(
            db.scalar(
                select(func.count())
                .select_from(Incident)
                .where(Incident.status.in_(OPEN_STATUSES))
            )
            or 0
        )

        agent_row = db.get(AdsAgentQuality, day)
        if agent_row is None:
            agent_row = AdsAgentQuality(stat_date=day)
            db.add(agent_row)
        agent_row.rca_total = rca_total
        agent_row.rca_accept_count = rca_accept
        agent_row.rca_accept_rate = _decimal_rate(rca_accept, rca_total)
        agent_row.runbook_exec_total = rb_total
        agent_row.runbook_exec_success = rb_success
        agent_row.runbook_success_rate = _decimal_rate(rb_success, rb_total)
        agent_row.kb_published_count = kb_pub
        agent_row.open_incident_count = open_count
        updated["agent"] += 1

        day += timedelta(days=1)

    db.commit()
    return updated


def _safe_float(value: float | None, default: float = 0.0) -> float:
    if value is None or not isfinite(value):
        return default
    return float(value)


def _query_prometheus_service_health() -> list[dict[str, Any]]:
    settings = get_settings()
    base = settings.prometheus_base_url.rstrip("/")
    queries = {
        "error_rate": (
            'sum(rate(http_requests_total{job=~"ecom-api-.*", status=~"5.."}[5m])) by (job)'
            " / "
            'sum(rate(http_requests_total{job=~"ecom-api-.*"}[5m])) by (job)'
        ),
        "p95_latency": (
            "histogram_quantile(0.95, "
            'sum(rate(http_request_duration_highr_seconds_bucket{job=~"ecom-api-.*"}[5m])) by (le, job)'
            ")"
        ),
    }
    results: dict[str, dict[str, float]] = {}
    try:
        with httpx.Client(timeout=settings.observability_http_timeout) as client:
            for key, promql in queries.items():
                resp = client.get(
                    f"{base}/api/v1/query",
                    params={"query": promql},
                )
                resp.raise_for_status()
                body = resp.json()
                for series in body.get("data", {}).get("result", []):
                    job = series.get("metric", {}).get("job", "unknown")
                    value = series.get("value")
                    if isinstance(value, list) and len(value) >= 2:
                        try:
                            results.setdefault(job, {})[key] = float(value[1])
                        except (TypeError, ValueError):
                            pass
    except Exception:
        return []

    items: list[dict[str, Any]] = []
    for job, metrics in results.items():
        err = _safe_float(metrics.get("error_rate")) * 100
        p95 = _safe_float(metrics.get("p95_latency"))
        items.append(
            {
                "service": job,
                "error_rate": round(err, 2),
                "p95_seconds": round(p95, 3),
            }
        )
    items.sort(key=lambda x: x.get("error_rate", 0), reverse=True)
    return items[:8]


def _alert_counts_24h(db: Session) -> list[dict[str, Any]]:
    since = datetime.now() - timedelta(hours=24)
    rows = list(
        db.scalars(
            select(AlertEvent).where(AlertEvent.created_at >= since)
        ).all()
    )
    buckets: dict[str, dict[str, set[str] | int]] = {}
    for alert in rows:
        hour_key = alert.created_at.strftime("%Y-%m-%d %H:00")
        bucket = buckets.setdefault(hour_key, {"raw": 0, "fps": set()})
        bucket["raw"] = int(bucket["raw"]) + 1
        fps = bucket["fps"]
        assert isinstance(fps, set)
        fps.add(alert.fingerprint)

    points: list[dict[str, Any]] = []
    for hour in sorted(buckets.keys()):
        bucket = buckets[hour]
        fps = bucket["fps"]
        assert isinstance(fps, set)
        points.append(
            {
                "hour": hour,
                "raw_count": bucket["raw"],
                "deduped_count": len(fps),
            }
        )
    return points


def _incident_funnel(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(
        select(Incident.status, func.count())
        .group_by(Incident.status)
        .order_by(func.count().desc())
    ).all()
    return [{"status": status, "count": int(count)} for status, count in rows]


def _top_root_causes(db: Session, limit: int = 8) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(Incident)
        .where(Incident.root_cause_preview.isnot(None))
        .order_by(Incident.updated_at.desc())
        .limit(200)
    ).all()
    counts: dict[str, int] = {}
    for inc in rows:
        key = (inc.root_cause_preview or "").strip()[:120]
        if not key:
            continue
        counts[key] = counts.get(key, 0) + 1
    ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    return [{"root_cause": k, "count": v} for k, v in ranked]


def _mttr_trend_30d(db: Session) -> list[dict[str, Any]]:
    since = _today() - timedelta(days=30)
    rows = db.scalars(
        select(AdsMttrDaily)
        .where(AdsMttrDaily.stat_date >= since)
        .order_by(AdsMttrDaily.stat_date.asc())
    ).all()
    if rows:
        return [
            {
                "date": str(r.stat_date),
                "mttr_avg_minutes": float(r.mttr_avg_minutes)
                if r.mttr_avg_minutes is not None
                else None,
                "incident_count": r.incident_count,
            }
            for r in rows
        ]

    # ADS 未刷新时现场计算
    fallback: list[dict[str, Any]] = []
    for offset in range(30, -1, -1):
        day = _today() - timedelta(days=offset)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = day_start + timedelta(days=1)
        resolved = list(
            db.scalars(
                select(Incident).where(
                    Incident.resolved_at >= day_start,
                    Incident.resolved_at < day_end,
                )
            ).all()
        )
        mttr_values = [
            (inc.resolved_at - inc.created_at).total_seconds() / 60.0
            for inc in resolved
            if inc.resolved_at and inc.created_at
        ]
        avg = round(sum(mttr_values) / len(mttr_values), 2) if mttr_values else None
        fallback.append(
            {
                "date": str(day),
                "mttr_avg_minutes": avg,
                "incident_count": len(resolved),
            }
        )
    return fallback


def get_dashboard_overview(db: Session) -> DashboardOverviewSchema:
    today = _today()
    today_start = datetime.combine(today, datetime.min.time())

    open_incidents = int(
        db.scalar(
            select(func.count())
            .select_from(Incident)
            .where(Incident.status.in_(OPEN_STATUSES))
        )
        or 0
    )
    today_alerts = int(
        db.scalar(
            select(func.count())
            .select_from(AlertEvent)
            .where(AlertEvent.created_at >= today_start)
        )
        or 0
    )

    mttr_row = db.get(AdsMttrDaily, today)
    if mttr_row and mttr_row.mttr_avg_minutes is not None:
        mttr_avg_minutes = float(mttr_row.mttr_avg_minutes)
    else:
        resolved_recent = list(
            db.scalars(
                select(Incident)
                .where(Incident.resolved_at.isnot(None))
                .order_by(Incident.resolved_at.desc())
                .limit(50)
            ).all()
        )
        mttr_vals = [
            (i.resolved_at - i.created_at).total_seconds() / 60.0
            for i in resolved_recent
            if i.resolved_at and i.created_at
        ]
        mttr_avg_minutes = round(sum(mttr_vals) / len(mttr_vals), 2) if mttr_vals else 0.0

    adoption = get_adoption_stats(db)
    service_health = _query_prometheus_service_health()
    if not service_health:
        # 无 Prometheus 时用告警聚合近似
        svc_rows = db.execute(
            select(AlertEvent.service, func.count())
            .where(
                AlertEvent.created_at >= datetime.now() - timedelta(hours=6),
                AlertEvent.status == "firing",
            )
            .group_by(AlertEvent.service)
            .order_by(func.count().desc())
            .limit(8)
        ).all()
        service_health = [
            {
                "service": svc or "unknown",
                "error_rate": float(count),
                "p95_seconds": 0,
            }
            for svc, count in svc_rows
        ]

    return DashboardOverviewSchema(
        core_kpi={
            "mttr_avg_minutes": mttr_avg_minutes,
            "open_incidents": open_incidents,
            "today_alerts": today_alerts,
        },
        alert_curve_24h=_alert_counts_24h(db),
        incident_funnel=_incident_funnel(db),
        service_health_top=service_health,
        rca_quality={
            "accept_rate": adoption.adoption_rate,
            "recommended_count": adoption.recommended_rca_count,
            "adopted_count": adoption.adopted_rca_count,
            "rca_accept_feedback_rate": _feedback_accept_rate(db),
        },
        mttr_trend_30d=_mttr_trend_30d(db),
        top_root_causes=_top_root_causes(db),
        runbook_success={
            "total_executions": adoption.total_executions,
            "successful_executions": adoption.successful_executions,
            "success_rate": adoption.execution_success_rate,
        },
    )


def _feedback_accept_rate(db: Session) -> float:
    total = int(
        db.scalar(select(func.count()).select_from(IncidentFeedback)) or 0
    )
    if total == 0:
        return 0.0
    accepts = int(
        db.scalar(
            select(func.count())
            .select_from(IncidentFeedback)
            .where(IncidentFeedback.verdict == "accept")
        )
        or 0
    )
    return round(accepts / total, 4)
