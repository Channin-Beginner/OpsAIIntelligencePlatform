import { apiGet } from '@opsai/shared'
import type { DashboardOverview } from '@opsai/shared'
import { http } from './client'

export function getDashboardOverview() {
  return apiGet<DashboardOverview>(http, '/api/v1/dashboard/overview')
}
