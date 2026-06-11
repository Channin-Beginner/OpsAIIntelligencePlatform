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
