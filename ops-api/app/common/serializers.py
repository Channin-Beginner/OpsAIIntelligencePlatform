from datetime import datetime

from app.models.alert_event import AlertEvent
from app.models.incident import Incident
from app.models.incident_timeline import IncidentTimeline
from app.schemas.common import (
    AlertEventSummary,
    IncidentDetailSchema,
    IncidentSchema,
    IncidentSummarySchema,
    TimelineEventSchema,
)


def format_dt(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def timeline_to_schema(event: IncidentTimeline) -> TimelineEventSchema:
    actor_name = None
    if event.actor is not None:
        actor_name = event.actor.display_name
    return TimelineEventSchema(
        id=event.id,
        incident_id=event.incident_id,
        event_type=event.event_type,
        content=event.content,
        actor_type=event.actor_type,
        actor_id=event.actor_id,
        actor_name=actor_name,
        metadata=event.metadata_json,
        created_at=format_dt(event.created_at) or "",
    )


def alert_to_summary(alert: AlertEvent) -> AlertEventSummary:
    return AlertEventSummary(
        id=alert.id,
        fingerprint=alert.fingerprint,
        severity=alert.severity,
        title=alert.title,
        status=alert.status,
        source=alert.source,
        created_at=format_dt(alert.created_at) or "",
    )


def incident_to_summary(incident: Incident, alert_count: int = 0) -> IncidentSummarySchema:
    owner_name = None
    if incident.owner is not None:
        owner_name = incident.owner.display_name
    return IncidentSummarySchema(
        id=incident.id,
        incident_no=incident.incident_no,
        title=incident.title,
        status=incident.status,
        severity=incident.severity,
        service=incident.service,
        owner_id=incident.owner_id,
        owner_name=owner_name,
        root_cause_preview=incident.root_cause_preview,
        alert_count=alert_count,
        created_at=format_dt(incident.created_at) or "",
        updated_at=format_dt(incident.updated_at) or "",
        acknowledged_at=format_dt(incident.acknowledged_at),
        resolved_at=format_dt(incident.resolved_at),
        closed_at=format_dt(incident.closed_at),
    )


def incident_to_schema(incident: Incident, alert_count: int = 0) -> IncidentSchema:
    summary = incident_to_summary(incident, alert_count=alert_count)
    return IncidentSchema(
        **summary.model_dump(),
        description=incident.description,
        primary_fingerprint=incident.primary_fingerprint,
    )


def incident_to_detail(
    incident: Incident,
    alert_count: int,
    related_alerts: list[AlertEvent],
    recent_timeline: list[IncidentTimeline],
) -> IncidentDetailSchema:
    base = incident_to_schema(incident, alert_count=alert_count)
    return IncidentDetailSchema(
        **base.model_dump(),
        related_alerts=[alert_to_summary(a) for a in related_alerts],
        recent_timeline=[timeline_to_schema(t) for t in recent_timeline],
    )
