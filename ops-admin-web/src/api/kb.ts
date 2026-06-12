import { apiDelete, apiGet, apiPatch, apiPost } from '@opsai/shared'
import type {
  KbArticle,
  KbArticleCreateRequest,
  KbArticleUpdateRequest,
  PageResult,
} from '@opsai/shared'
import { http } from './client'

export interface KbListParams {
  page?: number
  page_size?: number
  status?: string
  service?: string
  keyword?: string
  source_incident_id?: number
}

export function listKbArticles(params: KbListParams = {}) {
  return apiGet<PageResult<KbArticle>>(http, '/api/v1/kb/articles', { params })
}

export function createKbArticle(body: KbArticleCreateRequest) {
  return apiPost<KbArticle>(http, '/api/v1/kb/articles', body)
}

export function updateKbArticle(id: number, body: KbArticleUpdateRequest) {
  return apiPatch<KbArticle>(http, `/api/v1/kb/articles/${id}`, body)
}

export function publishKbArticle(id: number) {
  return apiPost<KbArticle>(http, `/api/v1/kb/articles/${id}/publish`)
}

export function unpublishKbArticle(id: number) {
  return apiPost<KbArticle>(http, `/api/v1/kb/articles/${id}/unpublish`)
}

export function deleteKbArticle(id: number) {
  return apiDelete(http, `/api/v1/kb/articles/${id}`)
}
