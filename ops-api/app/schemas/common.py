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


class UserSummarySchema(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    is_active: bool
    created_at: str
    updated_at: str


class RcaEvidenceItem(BaseModel):
    type: str
    source: str
    summary: str
    query: str | None = None
    detail: dict[str, Any] | list[Any] | None = None


class RcaResultSchema(BaseModel):
    id: int
    incident_id: int
    status: str
    hypothesis: str | None = None
    confidence: float | None = None
    evidence: list[RcaEvidenceItem | dict[str, Any]] = Field(default_factory=list)
    suggested_runbook_ids: list[int] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    model_name: str | None = None
    error_message: str | None = None
    created_at: str
    completed_at: str | None = None


class RcaTriggerRequest(BaseModel):
    force: bool = False


class IncidentFeedbackRequest(BaseModel):
    score: int = Field(ge=1, le=5)
    verdict: str
    comment: str | None = Field(default=None, max_length=2000)
    rca_result_id: int | None = None


class IncidentFeedbackSchema(BaseModel):
    id: int
    incident_id: int
    rca_result_id: int | None = None
    user_id: int | None = None
    user_name: str | None = None
    score: int
    verdict: str
    comment: str | None = None
    created_at: str


class RunbookStepSchema(BaseModel):
    order: int
    title: str
    description: str | None = None
    action_type: str = "manual"
    action: dict[str, Any] | None = None


class RunbookSchema(BaseModel):
    id: int
    title: str
    description: str | None = None
    steps: list[RunbookStepSchema | dict[str, Any]] = Field(default_factory=list)
    risk_level: str
    service_tags: list[str] = Field(default_factory=list)
    alert_names: list[str] = Field(default_factory=list)
    status: str
    created_at: str
    updated_at: str


class RunbookCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    description: str | None = Field(default=None, max_length=1024)
    steps: list[dict[str, Any]] = Field(min_length=1)
    risk_level: str = "low"
    service_tags: list[str] = Field(default_factory=list)
    alert_names: list[str] = Field(default_factory=list)


class RunbookUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=256)
    description: str | None = Field(default=None, max_length=1024)
    steps: list[dict[str, Any]] | None = None
    risk_level: str | None = None
    service_tags: list[str] | None = None
    alert_names: list[str] | None = None


class RunbookStepResultSchema(BaseModel):
    order: int | None = None
    title: str | None = None
    action_type: str | None = None
    status: str | None = None
    message: str | None = None
    error: str | None = None
    http: dict[str, Any] | None = None


class RunbookExecutionSchema(BaseModel):
    id: int
    runbook_id: int
    runbook_title: str | None = None
    incident_id: int
    rca_result_id: int | None = None
    status: str
    step_results: list[RunbookStepResultSchema | dict[str, Any]] = Field(default_factory=list)
    error_message: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    created_at: str


class RunbookExecutionStartRequest(BaseModel):
    runbook_id: int
    rca_result_id: int | None = None
    confirmed: bool = False


class RunbookAdoptionStatsSchema(BaseModel):
    recommended_rca_count: int
    adopted_rca_count: int
    adoption_rate: float
    total_executions: int
    successful_executions: int
    execution_success_rate: float


class KbArticleSchema(BaseModel):
    id: int
    title: str
    summary: str | None = None
    content: str
    tags_text: str | None = None
    service: str | None = None
    source_incident_id: int | None = None
    status: str
    created_at: str
    updated_at: str


class KbArticleCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=256)
    summary: str | None = Field(default=None, max_length=512)
    content: str = Field(min_length=1)
    tags_text: str | None = Field(default=None, max_length=512)
    service: str | None = Field(default=None, max_length=128)
    source_incident_id: int | None = None


class KbArticleUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=256)
    summary: str | None = Field(default=None, max_length=512)
    content: str | None = None
    tags_text: str | None = Field(default=None, max_length=512)
    service: str | None = Field(default=None, max_length=128)


class DashboardOverviewSchema(BaseModel):
    core_kpi: dict[str, Any]
    alert_curve_24h: list[dict[str, Any]]
    incident_funnel: list[dict[str, Any]]
    service_health_top: list[dict[str, Any]]
    rca_quality: dict[str, Any]
    mttr_trend_30d: list[dict[str, Any]]
    top_root_causes: list[dict[str, Any]]
    runbook_success: dict[str, Any]
