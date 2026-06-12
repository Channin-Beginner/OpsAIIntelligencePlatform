"""历史 Incident + KB 关键词检索（阶段三 3.B.4）。"""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.agent.rca.types import evidence_item
from app.models.incident import Incident
from app.models.kb_article import KbArticle

_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    tokens = [t.lower() for t in _TOKEN_RE.findall(text) if len(t) >= 2]
    seen: set[str] = set()
    unique: list[str] = []
    for token in tokens:
        if token not in seen:
            seen.add(token)
            unique.append(token)
    return unique[:12]


def _score_text(text: str | None, tokens: list[str]) -> int:
    if not text or not tokens:
        return 0
    lowered = text.lower()
    return sum(1 for token in tokens if token in lowered)


def _search_incidents(
    db: Session,
    *,
    query: str,
    service: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    tokens = _tokenize(query)
    stmt = select(Incident).order_by(Incident.updated_at.desc()).limit(200)
    if service:
        stmt = stmt.where(Incident.service == service)

    candidates = db.scalars(stmt).all()
    scored: list[tuple[int, Incident]] = []
    for incident in candidates:
        score = _score_text(incident.title, tokens)
        score += _score_text(incident.description, tokens) * 2
        score += _score_text(incident.root_cause_preview, tokens) * 3
        score += _score_text(incident.service, tokens)
        if score > 0:
            scored.append((score, incident))

    scored.sort(key=lambda item: item[0], reverse=True)
    results: list[dict[str, Any]] = []
    for score, incident in scored[:limit]:
        results.append(
            {
                "id": incident.id,
                "incident_no": incident.incident_no,
                "title": incident.title,
                "status": incident.status,
                "severity": incident.severity,
                "service": incident.service,
                "root_cause_preview": incident.root_cause_preview,
                "score": score,
            }
        )
    return results


def _search_kb_articles(
    db: Session,
    *,
    query: str,
    service: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    tokens = _tokenize(query)
    filters = [KbArticle.status == "published"]
    if service:
        filters.append(
            or_(KbArticle.service == service, KbArticle.service.is_(None))
        )

    candidates = db.scalars(
        select(KbArticle)
        .where(*filters)
        .order_by(KbArticle.updated_at.desc())
        .limit(200)
    ).all()

    scored: list[tuple[int, KbArticle]] = []
    for article in candidates:
        score = _score_text(article.title, tokens) * 2
        score += _score_text(article.summary, tokens)
        score += _score_text(article.content, tokens)
        score += _score_text(article.tags_text, tokens)
        if score > 0:
            scored.append((score, article))

    scored.sort(key=lambda item: item[0], reverse=True)
    results: list[dict[str, Any]] = []
    for score, article in scored[:limit]:
        preview = (article.content or "")[:400]
        results.append(
            {
                "id": article.id,
                "title": article.title,
                "summary": article.summary,
                "service": article.service,
                "content_preview": preview,
                "score": score,
            }
        )
    return results


def search_incident_context(
    db: Session,
    query: str,
    *,
    service: str | None = None,
    incident_limit: int = 5,
    kb_limit: int = 5,
) -> dict[str, Any]:
    """
    关键词检索历史 incident 与已发布 kb_article，供 RCA RAG 使用。
    """
    cleaned = query.strip()
    if not cleaned:
        raise ValueError("query 不能为空")

    incidents = _search_incidents(
        db, query=cleaned, service=service, limit=incident_limit
    )
    kb_articles = _search_kb_articles(
        db, query=cleaned, service=service, limit=kb_limit
    )

    parts: list[str] = []
    if incidents:
        parts.append(f"{len(incidents)} 条相似历史 Incident")
    if kb_articles:
        parts.append(f"{len(kb_articles)} 篇 KB 文章")
    summary = "；".join(parts) if parts else "未命中相似历史记录"

    return evidence_item(
        type="kb",
        source="incident_rag",
        summary=summary,
        query=cleaned,
        detail={
            "incidents": incidents,
            "kb_articles": kb_articles,
            "service_filter": service,
        },
    )
