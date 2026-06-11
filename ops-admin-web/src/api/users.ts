import { apiGet } from '@opsai/shared'
import type { PageResult, UserSummary } from '@opsai/shared'
import { http } from './client'

export function listUsers(page = 1, page_size = 50) {
  return apiGet<PageResult<UserSummary>>(http, '/api/v1/users', {
    params: { page, page_size },
  })
}
