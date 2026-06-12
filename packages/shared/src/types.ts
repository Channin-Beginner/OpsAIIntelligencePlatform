import type { AlertStatus, IncidentStatus, Severity, UserRole } from './enums'

export interface CommonResult<T> {
  code: number
  message: string
  data: T
}

export interface PageMeta {
  page: number
  page_size: number
  total: number
  total_pages: number
}

export interface PageResult<T> {
  items: T[]
  meta: PageMeta
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginData {
  access_token: string
  token_type: string
  user_id: number
  username: string
  display_name: string
  role: UserRole
}

export interface AlertEventSummary {
  id: number
  fingerprint: string
  severity: Severity
  title: string
  status: AlertStatus
  source: string
  created_at: string
}

export interface IncidentSummary {
  id: number
  incident_no: string
  title: string
  status: IncidentStatus
  severity: Severity
  service: string | null
  owner_id: number | null
  owner_name: string | null
  root_cause_preview: string | null
  alert_count: number
  created_at: string
  updated_at: string
  acknowledged_at: string | null
  resolved_at: string | null
  closed_at: string | null
}

export interface IncidentDetail extends IncidentSummary {
  description: string | null
  primary_fingerprint: string | null
  related_alerts: AlertEventSummary[]
  recent_timeline: TimelineEvent[]
}

export interface TimelineEvent {
  id: number
  incident_id: number
  event_type: string
  content: string
  actor_type: string
  actor_id: number | null
  actor_name: string | null
  metadata: Record<string, unknown> | null
  created_at: string
}

export interface IncidentPatchRequest {
  action?: string
  owner_id?: number
  severity?: Severity
  note?: string
  title?: string
  description?: string
}

export interface UserSummary {
  id: number
  username: string
  display_name: string
  role: UserRole
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface AuthUser {
  userId: number
  username: string
  displayName: string
  role: UserRole
  token: string
}

export interface RcaEvidenceItem {
  type: 'metric' | 'log' | 'trace' | 'kb' | string
  source: string
  summary: string
  query?: string | null
  detail?: Record<string, unknown> | unknown[] | null
}

export interface RcaResult {
  id: number
  incident_id: number
  status: 'pending' | 'running' | 'completed' | 'failed'
  hypothesis: string | null
  confidence: number | null
  evidence: RcaEvidenceItem[]
  suggested_runbook_ids: number[]
  suggested_actions: string[]
  model_name: string | null
  error_message: string | null
  created_at: string
  completed_at: string | null
}

export interface IncidentFeedback {
  id: number
  incident_id: number
  rca_result_id: number | null
  user_id: number | null
  user_name: string | null
  score: number
  verdict: 'accept' | 'reject'
  comment: string | null
  created_at: string
}

export interface IncidentFeedbackRequest {
  score: number
  verdict: 'accept' | 'reject'
  comment?: string
  rca_result_id?: number
}

export interface RunbookStep {
  order: number
  title: string
  description?: string | null
  action_type: 'manual' | 'http' | string
  action?: Record<string, unknown> | null
}

export interface Runbook {
  id: number
  title: string
  description: string | null
  steps: RunbookStep[]
  risk_level: 'low' | 'medium' | 'high' | string
  service_tags: string[]
  alert_names: string[]
  status: 'draft' | 'published' | string
  created_at: string
  updated_at: string
}

export interface RunbookCreateRequest {
  title: string
  description?: string | null
  steps: RunbookStep[]
  risk_level?: string
  service_tags?: string[]
  alert_names?: string[]
}

export interface RunbookUpdateRequest {
  title?: string
  description?: string | null
  steps?: RunbookStep[]
  risk_level?: string
  service_tags?: string[]
  alert_names?: string[]
}

export interface RunbookStepResult {
  order?: number
  title?: string
  action_type?: string
  status?: string
  message?: string
  error?: string
  http?: Record<string, unknown>
}

export interface RunbookExecution {
  id: number
  runbook_id: number
  runbook_title: string | null
  incident_id: number
  rca_result_id: number | null
  status: string
  step_results: RunbookStepResult[]
  error_message: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
}

export interface RunbookExecutionStartRequest {
  runbook_id: number
  rca_result_id?: number
  confirmed: boolean
}

export interface RunbookAdoptionStats {
  recommended_rca_count: number
  adopted_rca_count: number
  adoption_rate: number
  total_executions: number
  successful_executions: number
  execution_success_rate: number
}

export interface KbArticle {
  id: number
  title: string
  summary: string | null
  content: string
  tags_text: string | null
  service: string | null
  source_incident_id: number | null
  status: 'draft' | 'published' | string
  created_at: string
  updated_at: string
}

export interface KbArticleCreateRequest {
  title: string
  summary?: string | null
  content: string
  tags_text?: string | null
  service?: string | null
  source_incident_id?: number | null
}

export interface KbArticleUpdateRequest {
  title?: string
  summary?: string | null
  content?: string
  tags_text?: string | null
  service?: string | null
}

export interface DashboardOverview {
  core_kpi: {
    mttr_avg_minutes: number
    open_incidents: number
    today_alerts: number
  }
  alert_curve_24h: Array<{ hour: string; raw_count: number; deduped_count: number }>
  incident_funnel: Array<{ status: string; count: number }>
  service_health_top: Array<{ service: string; error_rate: number; p95_seconds: number }>
  rca_quality: {
    accept_rate: number
    recommended_count: number
    adopted_count: number
    rca_accept_feedback_rate: number
  }
  mttr_trend_30d: Array<{ date: string; mttr_avg_minutes: number | null; incident_count: number }>
  top_root_causes: Array<{ root_cause: string; count: number }>
  runbook_success: {
    total_executions: number
    successful_executions: number
    success_rate: number
  }
}
