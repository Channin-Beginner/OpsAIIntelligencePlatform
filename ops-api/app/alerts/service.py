from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.common.redis_client import get_redis_client
from app.config import get_settings
from app.models.alert_event import AlertEvent
from app.models.incident import Incident
from app.models.incident_alert_rel import IncidentAlertRel
from app.models.incident_timeline import IncidentTimeline
from app.common.serializers import alert_to_summary
from app.schemas.common import (
    AlertEventSummary,
    AlertmanagerAlert,
    AlertmanagerWebhookPayload,
    PageResult,
    WebhookResult,
    build_page_meta,
)

OPEN_STATUSES = ("open", "acknowledged", "investigating", "mitigated")
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).replace(tzinfo=None)
    except ValueError:
        return None


def _extract_severity(alert: AlertmanagerAlert, payload: AlertmanagerWebhookPayload) -> str:
    labels = alert.labels or {}
    common = payload.commonLabels or {}
    raw = labels.get("severity") or common.get("severity") or "medium"
    if raw in SEVERITY_ORDER:
        return raw
    return "medium"


def _extract_service(alert: AlertmanagerAlert, payload: AlertmanagerWebhookPayload) -> str | None:
    labels = alert.labels or {}
    common = payload.commonLabels or {}
    return labels.get("service") or common.get("service")


def _extract_title(alert: AlertmanagerAlert, payload: AlertmanagerWebhookPayload) -> str:
    annotations = alert.annotations or {}
    common_ann = payload.commonAnnotations or {}
    summary = annotations.get("summary") or common_ann.get("summary")
    if summary:
        return summary[:512]
    labels = alert.labels or {}
    alertname = labels.get("alertname") or "UnknownAlert"
    return f"Alert: {alertname}"[:512]


def _fingerprint_redis_key(fingerprint: str) -> str:
    return f"opsai:alert:fp:{fingerprint}"


def _generate_incident_no(db: Session) -> str:
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"INC-{today}-"
    count = db.scalar(
        select(func.count())
        .select_from(Incident)
        .where(Incident.incident_no.like(f"{prefix}%"))
    )
    return f"{prefix}{int(count or 0) + 1:04d}"


def _find_open_incident_by_fingerprint(db: Session, fingerprint: str) -> Incident | None:
    stmt = (
        select(Incident)
        .where(
            Incident.primary_fingerprint == fingerprint,
            Incident.status.in_(OPEN_STATUSES),
        )
        .order_by(Incident.created_at.desc())
        .limit(1)
    )
    return db.scalar(stmt)


def _link_alert_to_incident(
    db: Session,
    incident: Incident,
    alert: AlertEvent,
    merge_content: str | None = None,
) -> None:
    exists = db.scalar(
        select(IncidentAlertRel.id)
        .where(
            IncidentAlertRel.incident_id == incident.id,
            IncidentAlertRel.alert_event_id == alert.id,
        )
        .limit(1)
    )
    if exists:
        return
    db.add(
        IncidentAlertRel(
            incident_id=incident.id,
            alert_event_id=alert.id,
        )
    )
    content = merge_content or f"告警归并: {alert.title} (fingerprint={alert.fingerprint})"
    db.add(
        IncidentTimeline(
            incident_id=incident.id,
            event_type="alert_merged",
            content=content,
            actor_type="system",
            metadata_json={"alert_id": alert.id, "fingerprint": alert.fingerprint},
        )
    )


def _create_incident_from_alert(db: Session, alert: AlertEvent) -> Incident:
    incident = Incident(
        incident_no=_generate_incident_no(db),
        title=alert.title,
        description=alert.summary,
        status="open",
        severity=alert.severity,
        service=alert.service,
        primary_fingerprint=alert.fingerprint,
    )
    db.add(incident)
    db.flush()
    db.add(
        IncidentTimeline(
            incident_id=incident.id,
            event_type="system",
            content="系统自动建单",
            actor_type="system",
            metadata_json={"alert_id": alert.id, "fingerprint": alert.fingerprint},
        )
    )
    _link_alert_to_incident(db, incident, alert)
    return incident


def _persist_alert_event(
    db: Session,
    alert: AlertmanagerAlert,
    payload: AlertmanagerWebhookPayload,
) -> AlertEvent:
    labels = alert.labels or {}
    annotations = alert.annotations or {}
    severity = _extract_severity(alert, payload)
    service = _extract_service(alert, payload)
    title = _extract_title(alert, payload)
    summary = annotations.get("description") or annotations.get("summary")

    event = AlertEvent(
        fingerprint=alert.fingerprint,
        source="alertmanager",
        status=alert.status,
        severity=severity,
        alertname=labels.get("alertname"),
        service=service,
        title=title,
        summary=summary,
        labels_json=labels,
        annotations_json=annotations,
        starts_at=_parse_iso_datetime(alert.startsAt),
        ends_at=_parse_iso_datetime(alert.endsAt),
    )
    db.add(event)
    db.flush()
    return event


def process_single_alert(
    db: Session,
    alert: AlertmanagerAlert,
    payload: AlertmanagerWebhookPayload,
) -> tuple[AlertEvent, int | None, bool]:
    settings = get_settings()
    redis_client = get_redis_client()
    redis_key = _fingerprint_redis_key(alert.fingerprint)

    alert_event = _persist_alert_event(db, alert, payload)

    is_new_in_window = bool(
        redis_client.set(redis_key, "1", nx=True, ex=settings.alert_fingerprint_ttl_seconds)
    )

    if not is_new_in_window:
        open_incident = _find_open_incident_by_fingerprint(db, alert.fingerprint)
        if open_incident:
            _link_alert_to_incident(db, open_incident, alert_event)
            return alert_event, open_incident.id, False
        return alert_event, None, False

    open_incident = _find_open_incident_by_fingerprint(db, alert.fingerprint)
    if open_incident:
        _link_alert_to_incident(db, open_incident, alert_event)
        return alert_event, open_incident.id, False

    # 新 fingerprint 或 critical 且无开放 Incident 时建单
    incident = _create_incident_from_alert(db, alert_event)
    return alert_event, incident.id, True


def process_alertmanager_webhook(
    db: Session,
    payload: AlertmanagerWebhookPayload,
) -> WebhookResult:
    alert_event_ids: list[int] = []
    last_incident_id: int | None = None
    incident_created = False

    for alert in payload.alerts:
        event, incident_id, created = process_single_alert(db, alert, payload)
        alert_event_ids.append(event.id)
        if incident_id is not None:
            last_incident_id = incident_id
        if created:
            incident_created = True

    db.commit()

    return WebhookResult(
        processed_count=len(alert_event_ids),
        alert_event_ids=alert_event_ids,
        incident_id=last_incident_id,
        incident_created=incident_created,
    )


def list_alerts(
    db: Session,
    page: int,
    page_size: int,
    status: str | None = None,
    severity: str | None = None,
    source: str | None = None,
    service: str | None = None,
    fingerprint: str | None = None,
    keyword: str | None = None,
) -> PageResult[AlertEventSummary]:
    filters = []
    if status:
        filters.append(AlertEvent.status == status)
    if severity:
        filters.append(AlertEvent.severity == severity)
    if source:
        filters.append(AlertEvent.source == source)
    if service:
        filters.append(AlertEvent.service == service)
    if fingerprint:
        filters.append(AlertEvent.fingerprint == fingerprint)
    if keyword:
        filters.append(AlertEvent.title.like(f"%{keyword}%"))

    total = int(
        db.scalar(select(func.count()).select_from(AlertEvent).where(*filters)) or 0
    )
    alerts = db.scalars(
        select(AlertEvent)
        .where(*filters)
        .order_by(AlertEvent.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return PageResult(
        items=[alert_to_summary(alert) for alert in alerts],
        meta=build_page_meta(page, page_size, total),
    )
