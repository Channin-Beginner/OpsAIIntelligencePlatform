from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.common.exceptions import BadRequestError, NotFoundError
from app.common.serializers import (
    incident_to_detail,
    incident_to_schema,
    incident_to_summary,
    timeline_to_schema,
)
from app.incidents.state_machine import validate_action
from app.models.alert_event import AlertEvent
from app.models.incident import Incident
from app.models.incident_alert_rel import IncidentAlertRel
from app.models.incident_timeline import IncidentTimeline
from app.models.sys_user import SysUser
from app.schemas.common import (
    IncidentCreateRequest,
    IncidentDetailSchema,
    IncidentPatchRequest,
    IncidentSchema,
    IncidentSummarySchema,
    PageResult,
    TimelineCreateRequest,
    TimelineEventSchema,
    build_page_meta,
)

ACTION_STATUS_LABELS = {
    "acknowledge": "已确认",
    "start_investigation": "开始调查",
    "mitigate": "标记缓解",
    "resolve": "标记解决",
    "close": "关闭",
    "reopen_investigation": "重新调查",
}


def _get_incident_or_404(db: Session, incident_id: int) -> Incident:
    incident = db.scalar(
        select(Incident)
        .options(joinedload(Incident.owner))
        .where(Incident.id == incident_id)
    )
    if incident is None:
        raise NotFoundError(message="Incident 不存在", data={"incident_id": incident_id})
    return incident


def _count_alerts(db: Session, incident_id: int) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(IncidentAlertRel)
            .where(IncidentAlertRel.incident_id == incident_id)
        )
        or 0
    )


def _generate_incident_no(db: Session) -> str:
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"INC-{today}-"
    count = db.scalar(
        select(func.count())
        .select_from(Incident)
        .where(Incident.incident_no.like(f"{prefix}%"))
    )
    return f"{prefix}{int(count or 0) + 1:04d}"


def _add_timeline(
    db: Session,
    incident_id: int,
    event_type: str,
    content: str,
    actor_type: str = "user",
    actor_id: int | None = None,
    metadata: dict | None = None,
) -> IncidentTimeline:
    event = IncidentTimeline(
        incident_id=incident_id,
        event_type=event_type,
        content=content,
        actor_type=actor_type,
        actor_id=actor_id,
        metadata_json=metadata,
    )
    db.add(event)
    db.flush()
    return event


def list_incidents(
    db: Session,
    page: int,
    page_size: int,
    status: str | None = None,
    severity: str | None = None,
    owner_id: int | None = None,
    service: str | None = None,
    keyword: str | None = None,
) -> PageResult[IncidentSummarySchema]:
    filters = []
    if status:
        filters.append(Incident.status == status)
    if severity:
        filters.append(Incident.severity == severity)
    if owner_id is not None:
        filters.append(Incident.owner_id == owner_id)
    if service:
        filters.append(Incident.service == service)
    if keyword:
        filters.append(Incident.title.like(f"%{keyword}%"))

    total = int(
        db.scalar(select(func.count()).select_from(Incident).where(*filters)) or 0
    )
    stmt = (
        select(Incident)
        .options(joinedload(Incident.owner))
        .where(*filters)
        .order_by(Incident.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    incidents = db.scalars(stmt).unique().all()

    items = []
    for incident in incidents:
        alert_count = _count_alerts(db, incident.id)
        items.append(incident_to_summary(incident, alert_count=alert_count))

    return PageResult(
        items=items,
        meta=build_page_meta(page, page_size, total),
    )


def create_incident(
    db: Session,
    body: IncidentCreateRequest,
    actor_id: int | None = None,
) -> IncidentSchema:
    if body.owner_id is not None:
        owner = db.get(SysUser, body.owner_id)
        if owner is None:
            raise BadRequestError(message="owner_id 无效")

    incident = Incident(
        incident_no=_generate_incident_no(db),
        title=body.title,
        description=body.description,
        status="open",
        severity=body.severity,
        service=body.service,
        owner_id=body.owner_id,
    )
    db.add(incident)
    db.flush()

    _add_timeline(
        db,
        incident.id,
        event_type="system",
        content="人工创建 Incident",
        actor_type="user" if actor_id else "system",
        actor_id=actor_id,
    )
    db.commit()
    db.refresh(incident, attribute_names=["owner"])
    return incident_to_schema(incident, alert_count=0)


def get_incident_detail(db: Session, incident_id: int) -> IncidentDetailSchema:
    incident = _get_incident_or_404(db, incident_id)
    alert_count = _count_alerts(db, incident_id)

    rel_alert_ids = db.scalars(
        select(IncidentAlertRel.alert_event_id)
        .where(IncidentAlertRel.incident_id == incident_id)
        .order_by(IncidentAlertRel.created_at.desc())
    ).all()
    related_alerts: list[AlertEvent] = []
    if rel_alert_ids:
        linked = list(
            db.scalars(
                select(AlertEvent).where(AlertEvent.id.in_(rel_alert_ids))
            ).all()
        )
        seen_fingerprints: set[str] = set()
        for alert in linked:
            if alert.fingerprint in seen_fingerprints:
                continue
            seen_fingerprints.add(alert.fingerprint)
            latest = db.scalar(
                select(AlertEvent)
                .where(AlertEvent.fingerprint == alert.fingerprint)
                .order_by(AlertEvent.created_at.desc(), AlertEvent.id.desc())
                .limit(1)
            )
            if latest is not None:
                related_alerts.append(latest)

    recent_timeline = list(
        db.scalars(
            select(IncidentTimeline)
            .options(joinedload(IncidentTimeline.actor))
            .where(IncidentTimeline.incident_id == incident_id)
            .order_by(IncidentTimeline.created_at.desc())
            .limit(5)
        )
        .unique()
        .all()
    )

    return incident_to_detail(
        incident,
        alert_count=alert_count,
        related_alerts=related_alerts,
        recent_timeline=recent_timeline,
    )


def patch_incident(
    db: Session,
    incident_id: int,
    body: IncidentPatchRequest,
    actor_id: int | None = None,
) -> IncidentSchema:
    incident = _get_incident_or_404(db, incident_id)

    if body.title is not None:
        incident.title = body.title
    if body.description is not None:
        incident.description = body.description

    if body.action:
        target_status = validate_action(incident.status, body.action)

        if body.action == "assign":
            if body.owner_id is None:
                raise BadRequestError(message="assign 动作需要 owner_id")
            owner = db.get(SysUser, body.owner_id)
            if owner is None:
                raise BadRequestError(message="owner_id 无效")
            incident.owner_id = body.owner_id
            _add_timeline(
                db,
                incident.id,
                event_type="assignment",
                content=f"指派给 {owner.display_name}",
                actor_type="user",
                actor_id=actor_id,
                metadata={"owner_id": body.owner_id},
            )
        elif body.action == "update_severity":
            if body.severity is None:
                raise BadRequestError(message="update_severity 动作需要 severity")
            old = incident.severity
            incident.severity = body.severity
            _add_timeline(
                db,
                incident.id,
                event_type="severity_change",
                content=f"严重级别 {old} → {body.severity}",
                actor_type="user",
                actor_id=actor_id,
                metadata={"from": old, "to": body.severity},
            )
        elif body.action == "add_note":
            note = body.note or body.description
            if not note:
                raise BadRequestError(message="add_note 需要 note 或 description")
            _add_timeline(
                db,
                incident.id,
                event_type="note",
                content=note,
                actor_type="user",
                actor_id=actor_id,
            )
        elif target_status:
            old_status = incident.status
            incident.status = target_status
            now = datetime.now()
            if target_status == "acknowledged":
                incident.acknowledged_at = now
            elif target_status == "resolved":
                incident.resolved_at = now
            elif target_status == "closed":
                incident.closed_at = now
            elif target_status == "investigating" and body.action == "reopen_investigation":
                incident.resolved_at = None

            label = ACTION_STATUS_LABELS.get(body.action, body.action)
            content = f"{label}: {old_status} → {target_status}"
            if body.note:
                content = f"{content} — {body.note}"
            _add_timeline(
                db,
                incident.id,
                event_type="status_change",
                content=content,
                actor_type="user",
                actor_id=actor_id,
                metadata={
                    "from_status": old_status,
                    "to_status": target_status,
                    "action": body.action,
                },
            )
    elif body.owner_id is not None:
        owner = db.get(SysUser, body.owner_id)
        if owner is None:
            raise BadRequestError(message="owner_id 无效")
        incident.owner_id = body.owner_id
        _add_timeline(
            db,
            incident.id,
            event_type="assignment",
            content=f"指派给 {owner.display_name}",
            actor_type="user",
            actor_id=actor_id,
            metadata={"owner_id": body.owner_id},
        )

    db.commit()
    db.refresh(incident, attribute_names=["owner"])
    return incident_to_schema(incident, alert_count=_count_alerts(db, incident.id))


def list_timeline(
    db: Session,
    incident_id: int,
    page: int,
    page_size: int,
) -> PageResult[TimelineEventSchema]:
    _get_incident_or_404(db, incident_id)
    total = int(
        db.scalar(
            select(func.count())
            .select_from(IncidentTimeline)
            .where(IncidentTimeline.incident_id == incident_id)
        )
        or 0
    )
    events = db.scalars(
        select(IncidentTimeline)
        .options(joinedload(IncidentTimeline.actor))
        .where(IncidentTimeline.incident_id == incident_id)
        .order_by(IncidentTimeline.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).unique().all()

    return PageResult(
        items=[timeline_to_schema(e) for e in events],
        meta=build_page_meta(page, page_size, total),
    )


def create_timeline_event(
    db: Session,
    incident_id: int,
    body: TimelineCreateRequest,
    actor_id: int | None = None,
) -> TimelineEventSchema:
    _get_incident_or_404(db, incident_id)
    event = _add_timeline(
        db,
        incident_id,
        event_type=body.event_type,
        content=body.content,
        actor_type="user",
        actor_id=actor_id,
        metadata=body.metadata,
    )
    db.commit()
    db.refresh(event, attribute_names=["actor"])
    return timeline_to_schema(event)
