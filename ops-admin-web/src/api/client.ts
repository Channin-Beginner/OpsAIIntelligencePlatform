import { createHttpClient } from '@opsai/shared'

const baseURL = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8280'

export const http = createHttpClient(baseURL)
