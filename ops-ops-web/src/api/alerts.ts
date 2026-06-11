import { apiGet } from '@opsai/shared'
import type { AlertEventSummary, PageResult } from '@opsai/shared'
import { http } from './client'

export interface AlertListParams {
  page?: number
  page_size?: number
  status?: string
  severity?: string
  source?: string
  service?: string
  fingerprint?: string
  keyword?: string
}

export function listAlerts(params: AlertListParams = {}) {
  return apiGet<PageResult<AlertEventSummary>>(http, '/api/v1/alerts', { params })
}
