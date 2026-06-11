import { apiPost } from '@opsai/shared'
import type { LoginData, LoginRequest } from '@opsai/shared'
import { http } from './client'

export function login(body: LoginRequest) {
  return apiPost<LoginData>(http, '/api/v1/auth/login', body)
}
