"""Runbook 推荐：按 service / alertname 匹配已发布手册（阶段四 4.3）。"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.runbook import Runbook


def list_published_runbooks(db: Session) -> list[Runbook]:
    return list(
        db.scalars(
            select(Runbook)
            .where(Runbook.status == "published")
            .order_by(Runbook.id.asc())
        ).all()
    )


def match_runbook_ids(
    db: Session,
    *,
    service: str | None,
    alertname: str | None,
    limit: int = 3,
) -> list[int]:
    """规则匹配：service_tags 与 alert_names 命中则推荐。"""
    runbooks = list_published_runbooks(db)
    scored: list[tuple[int, int]] = []

    for rb in runbooks:
        score = 0
        tags = rb.service_tags or []
        alerts = rb.alert_names or []
        if service and service in tags:
            score += 2
        if alertname and alertname in alerts:
            score += 3
        if score > 0:
            scored.append((score, rb.id))

    scored.sort(key=lambda x: (-x[0], x[1]))
    return [rb_id for _, rb_id in scored[:limit]]


def runbooks_for_llm_context(db: Session) -> list[dict]:
    """供 RCA LLM 使用的精简 Runbook 目录。"""
    items = []
    for rb in list_published_runbooks(db):
        items.append(
            {
                "id": rb.id,
                "title": rb.title,
                "risk_level": rb.risk_level,
                "service_tags": rb.service_tags or [],
                "alert_names": rb.alert_names or [],
            }
        )
    return items
