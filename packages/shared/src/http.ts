import axios, {
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios'
import type { CommonResult } from './types'

const TOKEN_KEY = 'opsai_access_token'

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setStoredToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

export function createHttpClient(baseURL: string): AxiosInstance {
  const client = axios.create({
    baseURL,
    timeout: 30000,
    headers: { 'Content-Type': 'application/json' },
  })

  client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
    const token = getStoredToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  })

  client.interceptors.response.use(
    (response: AxiosResponse) => {
      const body = response.data as CommonResult<unknown>
      if (body && typeof body.code === 'number' && body.code !== 200) {
        return Promise.reject(new Error(body.message || '请求失败'))
      }
      return response
    },
    (error: { response?: { status?: number; data?: { message?: string } }; message?: string }) => {
      if (error.response?.status === 401) {
        clearStoredToken()
        const loginPath = window.location.pathname.startsWith('/admin') ? '/login' : '/login'
        if (!window.location.pathname.includes('/login')) {
          window.location.href = loginPath
        }
      }
      const message =
        error.response?.data?.message || error.message || '网络请求失败'
      return Promise.reject(new Error(message))
    },
  )

  return client
}

export async function apiGet<T>(
  client: AxiosInstance,
  url: string,
  config?: AxiosRequestConfig,
): Promise<T> {
  const { data } = await client.get<CommonResult<T>>(url, config)
  return data.data
}

export async function apiPost<T>(
  client: AxiosInstance,
  url: string,
  body?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> {
  const { data } = await client.post<CommonResult<T>>(url, body, config)
  return data.data
}

export async function apiPatch<T>(
  client: AxiosInstance,
  url: string,
  body?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> {
  const { data } = await client.patch<CommonResult<T>>(url, body, config)
  return data.data
}

export async function apiDelete(
  client: AxiosInstance,
  url: string,
  config?: AxiosRequestConfig,
): Promise<void> {
  await client.delete(url, config)
}
