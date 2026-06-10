from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class PageResult(BaseModel, Generic[T]):
    items: list[T]
    meta: PageMeta


def build_page_meta(page: int, page_size: int, total: int) -> PageMeta:
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return PageMeta(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
    )


class HealthData(BaseModel):
    status: str
    service: str
    version: str


Severity = str
IncidentStatus = str
IncidentAction = str
TimelineEventType = str
AlertStatus = str


class AlertmanagerAlert(BaseModel):
    status: AlertStatus
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)
    startsAt: str | None = None
    endsAt: str | None = None
    generatorURL: str | None = None
    fingerprint: str


class AlertmanagerWebhookPayload(BaseModel):
    status: AlertStatus
    receiver: str | None = None
    groupLabels: dict[str, str] = Field(default_factory=dict)
    commonLabels: dict[str, str] = Field(default_factory=dict)
    commonAnnotations: dict[str, str] = Field(default_factory=dict)
    externalURL: str | None = None
    alerts: list[AlertmanagerAlert] = Field(min_length=1)


class WebhookResult(BaseModel):
    processed_count: int
    alert_event_ids: list[int]
    incident_id: int | None = None
    incident_created: bool = False


class AlertEventSummary(BaseModel):
    id: int
    fingerprint: str
    severity: Severity
    title: str
    status: AlertStatus
    source: str
    created_at: str

    model_config = {"from_attributes": True}


class TimelineEventSchema(BaseModel):
    id: int
    incident_id: int
    event_type: TimelineEventType
    content: str
    actor_type: str
    actor_id: int | None = None
    actor_name: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: str

    model_config = {"from_attributes": True}


class IncidentSummarySchema(BaseModel):
    id: int
    incident_no: str
    title: str
    status: IncidentStatus
    severity: Severity
    service: str | None = None
    owner_id: int | None = None
    owner_name: str | None = None
    root_cause_preview: str | None = None
    alert_count: int = 0
    created_at: str
    updated_at: str
    acknowledged_at: str | None = None
    resolved_at: str | None = None
    closed_at: str | None = None

    model_config = {"from_attributes": True}


class IncidentSchema(IncidentSummarySchema):
    description: str | None = None
    primary_fingerprint: str | None = None


class IncidentDetailSchema(IncidentSchema):
    related_alerts: list[AlertEventSummary] = Field(default_factory=list)
    recent_timeline: list[TimelineEventSchema] = Field(default_factory=list)


class IncidentCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    description: str | None = Field(default=None, max_length=4000)
    severity: Severity
    service: str | None = Field(default=None, max_length=128)
    owner_id: int | None = None


class IncidentPatchRequest(BaseModel):
    action: IncidentAction | None = None
    owner_id: int | None = None
    severity: Severity | None = None
    note: str | None = Field(default=None, max_length=2000)
    title: str | None = Field(default=None, max_length=256)
    description: str | None = Field(default=None, max_length=4000)


class TimelineCreateRequest(BaseModel):
    event_type: TimelineEventType = "note"
    content: str = Field(min_length=1, max_length=2000)
    metadata: dict[str, Any] | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    display_name: str
    role: str
