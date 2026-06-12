"""Postmortem Agent：Incident resolved 后生成 KB 复盘草稿（阶段五 5.3）。"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.rca.llm_client import chat_json
from app.config import get_settings
from app.incidents.service import _add_timeline, _get_incident_or_404
from app.models.alert_event import AlertEvent
from app.models.incident_alert_rel import IncidentAlertRel
from app.models.incident_feedback import IncidentFeedback
from app.models.incident_timeline import IncidentTimeline
from app.models.kb_article import KbArticle
from app.models.rca_result import RcaResult

_SYSTEM_PROMPT = """你是 SRE 事后复盘专家。根据 Incident 全链路信息，输出严格 JSON：
{
  "title": "复盘标题（中文，≤80字）",
  "summary": "一句话摘要（≤200字）",
  "content": "Markdown 格式复盘正文，含：事件概述、时间线、根因分析、影响范围、处置过程、改进项（Action Items）",
  "tags": ["标签1", "标签2"]
}
规则：
1. 基于提供的 timeline / RCA / 反馈撰写，不可编造未出现的事实。
2. content 使用 Markdown 二级标题（##）。
3. 只输出 JSON。"""


def _gather_context(db: Session, incident_id: int) -> dict[str, Any]:
    incident = _get_incident_or_404(db, incident_id)

    rel_alert_ids = db.scalars(
        select(IncidentAlertRel.alert_event_id).where(
            IncidentAlertRel.incident_id == incident_id
        )
    ).all()
    alerts: list[AlertEvent] = []
    if rel_alert_ids:
        alerts = list(
            db.scalars(select(AlertEvent).where(AlertEvent.id.in_(rel_alert_ids))).all()
        )

    timeline = list(
        db.scalars(
            select(IncidentTimeline)
            .where(IncidentTimeline.incident_id == incident_id)
            .order_by(IncidentTimeline.created_at.asc())
        ).all()
    )

    rca_rows = list(
        db.scalars(
            select(RcaResult)
            .where(RcaResult.incident_id == incident_id)
            .order_by(RcaResult.created_at.desc())
            .limit(3)
        ).all()
    )

    feedback_rows = list(
        db.scalars(
            select(IncidentFeedback)
            .where(IncidentFeedback.incident_id == incident_id)
            .order_by(IncidentFeedback.created_at.desc())
            .limit(5)
        ).all()
    )

    return {
        "incident": incident,
        "alerts": alerts,
        "timeline": timeline,
        "rca_results": rca_rows,
        "feedback": feedback_rows,
    }


def _fallback_draft(ctx: dict[str, Any]) -> dict[str, Any]:
    incident = ctx["incident"]
    rca = ctx["rca_results"][0] if ctx["rca_results"] else None
    hypothesis = rca.hypothesis if rca else (incident.root_cause_preview or "待补充根因")
    timeline_lines = [
        f"- {e.created_at.strftime('%Y-%m-%d %H:%M')} [{e.event_type}] {e.content}"
        for e in ctx["timeline"][:12]
    ]
    content = "\n".join(
        [
            "## 事件概述",
            f"{incident.title}（{incident.incident_no}），服务 {incident.service or '未知'}，"
            f"严重级别 {incident.severity}。",
            "",
            "## 时间线",
            *(timeline_lines or ["- （无时间线记录）"]),
            "",
            "## 根因分析",
            hypothesis,
            "",
            "## 改进项",
            "- 完善监控与 Runbook 覆盖",
            "- 将本次处置沉淀为 KB 并发布",
        ]
    )
    tags = ["postmortem", incident.service or "opsai"]
    if incident.primary_fingerprint:
        tags.append(incident.primary_fingerprint[:32])
    return {
        "title": f"[复盘] {incident.title}"[:256],
        "summary": hypothesis[:512] if hypothesis else incident.title[:512],
        "content": content,
        "tags": tags,
    }


def _llm_draft(ctx: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    incident = ctx["incident"]
    payload = {
        "incident": {
            "incident_no": incident.incident_no,
            "title": incident.title,
            "description": incident.description,
            "service": incident.service,
            "severity": incident.severity,
            "status": incident.status,
            "root_cause_preview": incident.root_cause_preview,
            "created_at": str(incident.created_at),
            "resolved_at": str(incident.resolved_at),
        },
        "alerts": [
            {
                "title": a.title,
                "alertname": a.alertname,
                "source": a.source,
                "severity": a.severity,
            }
            for a in ctx["alerts"][:5]
        ],
        "timeline": [
            {"type": e.event_type, "content": e.content, "at": str(e.created_at)}
            for e in ctx["timeline"][:20]
        ],
        "rca": [
            {
                "hypothesis": r.hypothesis,
                "confidence": float(r.confidence) if r.confidence is not None else None,
                "suggested_actions": r.suggested_actions_json,
            }
            for r in ctx["rca_results"]
        ],
        "feedback": [
            {"verdict": f.verdict, "score": f.score, "comment": f.comment}
            for f in ctx["feedback"]
        ],
    }
    user_prompt = json.dumps(payload, ensure_ascii=False, indent=2)
    parsed, model = chat_json(system_prompt=_SYSTEM_PROMPT, user_prompt=user_prompt)
    return parsed, model


def generate_postmortem_draft(db: Session, incident_id: int) -> KbArticle | None:
    """为已 resolved/closed 的 Incident 生成 KB 复盘草稿（幂等：同 incident 仅一条 draft）。"""
    ctx = _gather_context(db, incident_id)
    incident = ctx["incident"]

    if incident.status not in ("resolved", "closed"):
        return None

    existing = db.scalar(
        select(KbArticle)
        .where(
            KbArticle.source_incident_id == incident_id,
            KbArticle.status == "draft",
        )
        .limit(1)
    )
    if existing is not None:
        return existing

    settings = get_settings()
    model_name: str | None = None
    try:
        if settings.llm_api_key.strip():
            draft, model_name = _llm_draft(ctx)
        else:
            draft = _fallback_draft(ctx)
    except Exception:
        draft = _fallback_draft(ctx)

    tags = draft.get("tags") or []
    if isinstance(tags, list):
        tags_text = ",".join(str(t) for t in tags)
    else:
        tags_text = "postmortem"

    article = KbArticle(
        title=str(draft.get("title") or f"[复盘] {incident.title}")[:256],
        summary=(draft.get("summary") or "")[:512] or None,
        content=str(draft.get("content") or ""),
        tags_text=tags_text[:512],
        service=incident.service,
        source_incident_id=incident_id,
        status="draft",
    )
    db.add(article)
    db.flush()

    _add_timeline(
        db,
        incident_id,
        event_type="system",
        content=f"Postmortem Agent 已生成复盘草稿（KB #{article.id}）",
        actor_type="system",
        metadata={"kb_article_id": article.id, "model": model_name, "kind": "postmortem"},
    )
    db.commit()
    db.refresh(article)
    return article
