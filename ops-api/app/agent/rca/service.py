"""RCA API 服务层：Redis 锁、持久化、反馈（阶段三 3.C.3 / 3.C.5）。"""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.rca.rca_agent import analyze_incident
from app.common.exceptions import BadRequestError, ConflictError, NotFoundError
from app.common.redis_client import get_redis_client
from app.common.serializers import format_dt
from app.config import get_settings
from app.incidents.service import _add_timeline, _get_incident_or_404
from app.models.alert_event import AlertEvent
from app.models.incident_alert_rel import IncidentAlertRel
from app.models.incident_feedback import IncidentFeedback
from app.models.rca_result import RcaResult
from app.schemas.common import (
    IncidentFeedbackRequest,
    IncidentFeedbackSchema,
    RcaResultSchema,
    RcaTriggerRequest,
)

logger = logging.getLogger("ops.rca")

RCA_LOCK_PREFIX = "rca:lock:"
RCA_LOCK_TTL_SECONDS = 300


def _rca_lock_key(incident_id: int) -> str:
    return f"{RCA_LOCK_PREFIX}{incident_id}"


def _acquire_rca_lock(incident_id: int) -> bool:
    client = get_redis_client()
    return bool(client.set(_rca_lock_key(incident_id), "1", nx=True, ex=RCA_LOCK_TTL_SECONDS))


def _release_rca_lock(incident_id: int) -> None:
    try:
        get_redis_client().delete(_rca_lock_key(incident_id))
    except Exception:
        pass


def _get_primary_alert(db: Session, incident_id: int) -> AlertEvent | None:
    rel = db.scalar(
        select(IncidentAlertRel)
        .where(IncidentAlertRel.incident_id == incident_id)
        .order_by(IncidentAlertRel.created_at.desc())
        .limit(1)
    )
    if rel is None:
        return None
    return db.get(AlertEvent, rel.alert_event_id)


def rca_result_to_schema(row: RcaResult) -> RcaResultSchema:
    confidence = None
    if row.confidence is not None:
        confidence = float(row.confidence)
    return RcaResultSchema(
        id=row.id,
        incident_id=row.incident_id,
        status=row.status,
        hypothesis=row.hypothesis,
        confidence=confidence,
        evidence=row.evidence_json or [],
        suggested_runbook_ids=row.suggested_runbook_ids or [],
        suggested_actions=row.suggested_actions or [],
        model_name=row.model_name,
        error_message=row.error_message,
        created_at=format_dt(row.created_at) or "",
        completed_at=format_dt(row.completed_at),
    )


def feedback_to_schema(row: IncidentFeedback) -> IncidentFeedbackSchema:
    user_name = None
    if row.user is not None:
        user_name = row.user.display_name
    return IncidentFeedbackSchema(
        id=row.id,
        incident_id=row.incident_id,
        rca_result_id=row.rca_result_id,
        user_id=row.user_id,
        user_name=user_name,
        score=row.score,
        verdict=row.verdict,
        comment=row.comment,
        created_at=format_dt(row.created_at) or "",
    )


def get_latest_rca_result(db: Session, incident_id: int) -> RcaResultSchema | None:
    _get_incident_or_404(db, incident_id)
    row = db.scalar(
        select(RcaResult)
        .where(RcaResult.incident_id == incident_id)
        .order_by(RcaResult.created_at.desc())
        .limit(1)
    )
    if row is None:
        return None
    return rca_result_to_schema(row)


def trigger_rca(
    db: Session,
    incident_id: int,
    body: RcaTriggerRequest,
    *,
    actor_id: int | None = None,
) -> RcaResultSchema:
    incident = _get_incident_or_404(db, incident_id)

    if not body.force:
        running = db.scalar(
            select(RcaResult)
            .where(
                RcaResult.incident_id == incident_id,
                RcaResult.status.in_(("pending", "running")),
            )
            .limit(1)
        )
        if running is not None:
            raise ConflictError(
                message="该 Incident 已有进行中的 RCA 任务",
                data={"rca_result_id": running.id},
            )

    if not _acquire_rca_lock(incident_id):
        raise ConflictError(message="RCA 正在执行中，请稍后再试")

    row = RcaResult(
        incident_id=incident_id,
        status="running",
        model_name=get_settings().llm_model,
    )
    db.add(row)
    db.flush()

    _add_timeline(
        db,
        incident_id,
        event_type="system",
        content="RCA Agent 开始分析",
        actor_type="system",
        actor_id=actor_id,
        metadata={"rca_result_id": row.id},
    )
    db.commit()
    logger.info("rca started incident_id=%s rca_result_id=%s", incident_id, row.id)

    try:
        primary_alert = _get_primary_alert(db, incident_id)
        analysis = analyze_incident(db, incident, primary_alert=primary_alert)

        preview = (analysis.get("hypothesis") or "")[:512]
        row.status = "completed"
        row.hypothesis = analysis.get("hypothesis")
        row.confidence = Decimal(str(analysis.get("confidence", 0.5)))
        row.evidence_json = analysis.get("evidence") or []
        row.suggested_runbook_ids = analysis.get("suggested_runbook_ids") or []
        row.suggested_actions = analysis.get("suggested_actions") or []
        row.model_name = analysis.get("model_name") or row.model_name
        row.completed_at = datetime.now()
        incident.root_cause_preview = preview

        _add_timeline(
            db,
            incident_id,
            event_type="system",
            content=f"RCA 完成：{preview}",
            actor_type="system",
            actor_id=actor_id,
            metadata={
                "rca_result_id": row.id,
                "confidence": float(row.confidence) if row.confidence else None,
            },
        )
        db.commit()
        db.refresh(row)
        logger.info(
            "rca completed incident_id=%s rca_result_id=%s confidence=%s",
            incident_id,
            row.id,
            float(row.confidence) if row.confidence else None,
        )
        return rca_result_to_schema(row)
    except Exception as exc:
        logger.exception(
            "rca failed incident_id=%s rca_result_id=%s",
            incident_id,
            row.id,
        )
        row.status = "failed"
        row.error_message = str(exc)[:512]
        row.completed_at = datetime.now()
        _add_timeline(
            db,
            incident_id,
            event_type="system",
            content=f"RCA 失败：{row.error_message}",
            actor_type="system",
            actor_id=actor_id,
            metadata={"rca_result_id": row.id},
        )
        db.commit()
        db.refresh(row)
        return rca_result_to_schema(row)
    finally:
        _release_rca_lock(incident_id)


def submit_feedback(
    db: Session,
    incident_id: int,
    body: IncidentFeedbackRequest,
    *,
    actor_id: int | None = None,
) -> IncidentFeedbackSchema:
    _get_incident_or_404(db, incident_id)

    rca_result_id = body.rca_result_id
    if body.verdict not in ("accept", "reject"):
        raise BadRequestError(message="verdict 必须为 accept 或 reject")

    rca_result_id = body.rca_result_id
    if rca_result_id is not None:
        rca_row = db.get(RcaResult, rca_result_id)
        if rca_row is None or rca_row.incident_id != incident_id:
            raise BadRequestError(message="rca_result_id 与 Incident 不匹配")

    row = IncidentFeedback(
        incident_id=incident_id,
        rca_result_id=rca_result_id,
        user_id=actor_id,
        score=body.score,
        verdict=body.verdict,
        comment=body.comment,
    )
    db.add(row)

    verdict_label = "采纳" if body.verdict == "accept" else "驳回"
    note = body.comment or ""
    content = f"RCA 反馈：{verdict_label}（{body.score} 分）"
    if note:
        content = f"{content} — {note}"

    _add_timeline(
        db,
        incident_id,
        event_type="note",
        content=content,
        actor_type="user",
        actor_id=actor_id,
        metadata={
            "feedback_id": None,
            "rca_result_id": rca_result_id,
            "score": body.score,
            "verdict": body.verdict,
        },
    )
    db.commit()
    db.refresh(row, attribute_names=["user"])
    return feedback_to_schema(row)
