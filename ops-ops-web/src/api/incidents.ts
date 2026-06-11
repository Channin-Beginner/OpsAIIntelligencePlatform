import { apiGet, apiPatch } from '@opsai/shared'
import type {
  IncidentDetail,
  IncidentPatchRequest,
  IncidentSummary,
  PageResult,
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
