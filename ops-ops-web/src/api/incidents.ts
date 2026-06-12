import { apiGet, apiPatch, apiPost } from '@opsai/shared'
import type {
  IncidentDetail,
  IncidentFeedback,
  IncidentFeedbackRequest,
  IncidentPatchRequest,
  IncidentSummary,
  PageResult,
  RcaResult,
  TimelineEvent,
} from '@opsai/shared'
import { http } from './client'

export interface IncidentListParams {
  page?: number
  page_size?: number
  status?: string
  severity?: string
  owner_id?: number
  service?: string
  keyword?: string
}

export function listIncidents(params: IncidentListParams = {}) {
  return apiGet<PageResult<IncidentSummary>>(http, '/api/v1/incidents', { params })
}

export function getIncident(id: number) {
  return apiGet<IncidentDetail>(http, `/api/v1/incidents/${id}`)
}

export function patchIncident(id: number, body: IncidentPatchRequest) {
  return apiPatch<IncidentSummary>(http, `/api/v1/incidents/${id}`, body)
}

export function listTimeline(incidentId: number, page = 1, page_size = 50) {
  return apiGet<PageResult<TimelineEvent>>(http, `/api/v1/incidents/${incidentId}/timeline`, {
    params: { page, page_size },
  })
}

export function getIncidentRca(incidentId: number) {
  return apiGet<RcaResult | null>(http, `/api/v1/incidents/${incidentId}/rca`)
}

/** RCA 会拉取指标/日志/链路并调用 LLM，通常超过默认 30s。 */
const RCA_REQUEST_TIMEOUT_MS = 180_000

export function triggerIncidentRca(incidentId: number, force = false) {
  return apiPost<RcaResult>(
    http,
    `/api/v1/incidents/${incidentId}/rca`,
    { force },
    { timeout: RCA_REQUEST_TIMEOUT_MS },
  )
}

export function submitIncidentFeedback(incidentId: number, body: IncidentFeedbackRequest) {
  return apiPost<IncidentFeedback>(http, `/api/v1/incidents/${incidentId}/feedback`, body)
}
