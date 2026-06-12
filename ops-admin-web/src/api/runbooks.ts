import { apiDelete, apiGet, apiPatch, apiPost } from '@opsai/shared'
import type {
  PageResult,
  Runbook,
  RunbookAdoptionStats,
  RunbookCreateRequest,
  RunbookUpdateRequest,
} from '@opsai/shared'
import { http } from './client'

export interface RunbookListParams {
  page?: number
  page_size?: number
  status?: string
  service?: string
}

export function listRunbooks(params: RunbookListParams = {}) {
  return apiGet<PageResult<Runbook>>(http, '/api/v1/runbooks', { params })
}

export function getRunbook(id: number) {
  return apiGet<Runbook>(http, `/api/v1/runbooks/${id}`)
}

export function createRunbook(body: RunbookCreateRequest) {
  return apiPost<Runbook>(http, '/api/v1/runbooks', body)
}

export function updateRunbook(id: number, body: RunbookUpdateRequest) {
  return apiPatch<Runbook>(http, `/api/v1/runbooks/${id}`, body)
}

export function publishRunbook(id: number) {
  return apiPost<Runbook>(http, `/api/v1/runbooks/${id}/publish`)
}

export function unpublishRunbook(id: number) {
  return apiPost<Runbook>(http, `/api/v1/runbooks/${id}/unpublish`)
}

export function deleteRunbook(id: number) {
  return apiDelete(http, `/api/v1/runbooks/${id}`)
}

export function getRunbookAdoptionStats() {
  return apiGet<RunbookAdoptionStats>(http, '/api/v1/runbooks/stats/adoption')
}
