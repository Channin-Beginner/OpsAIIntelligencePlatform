import { apiGet, apiPost } from '@opsai/shared'
import type { PageResult, Runbook, RunbookExecution, RunbookExecutionStartRequest } from '@opsai/shared'
import { http } from './client'

export function listPublishedRunbooks(page = 1, page_size = 50) {
  return apiGet<PageResult<Runbook>>(http, '/api/v1/runbooks', {
    params: { published_only: true, page, page_size },
  })
}

export function getRunbook(id: number) {
  return apiGet<Runbook>(http, `/api/v1/runbooks/${id}`)
}

export function listRunbookExecutions(incidentId: number, page = 1, page_size = 20) {
  return apiGet<PageResult<RunbookExecution>>(
    http,
    `/api/v1/incidents/${incidentId}/runbook-executions`,
    { params: { page, page_size } },
  )
}

/** Runbook 可能含多步 HTTP，留足超时。 */
const RUNBOOK_EXEC_TIMEOUT_MS = 60_000

export function startRunbookExecution(incidentId: number, body: RunbookExecutionStartRequest) {
  return apiPost<RunbookExecution>(
    http,
    `/api/v1/incidents/${incidentId}/runbook-executions`,
    body,
    { timeout: RUNBOOK_EXEC_TIMEOUT_MS },
  )
}
