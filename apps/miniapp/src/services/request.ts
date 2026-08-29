import Taro from '@tarojs/taro'
import { authService } from './auth'

export class ApiError extends Error {
  constructor(public status: number, message: string, public code?: string) {
    super(message)
    this.name = 'ApiError'
  }
}

const API_BASE = (process.env.TARO_APP_API_BASE || 'http://127.0.0.1:8000/api/v1').replace(/\/$/, '')

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  data?: unknown
  query?: Record<string, string | number | boolean | undefined>
}

function buildUrl(path: string, query?: RequestOptions['query']): string {
  const qs = Object.entries(query || {})
    .filter(([, value]) => value !== undefined)
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`)
    .join('&')
  return `${API_BASE}${path}${qs ? `?${qs}` : ''}`
}

async function send<T>(url: string, options: RequestOptions): Promise<T> {
  const token = authService.getToken()
  const response = await Taro.request<T>({
    url,
    method: options.method || 'GET',
    data: options.data,
    timeout: 12000,
    header: {
      'content-type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  })
  if (response.statusCode < 200 || response.statusCode >= 300) {
    const body = response.data as unknown as { detail?: string | { message?: string; code?: string }; message?: string }
    const detail = body?.detail
    const message = typeof detail === 'string' ? detail : detail?.message || body?.message || `请求失败 (${response.statusCode})`
    throw new ApiError(response.statusCode, message, typeof detail === 'object' ? detail.code : undefined)
  }
  return response.data
}

export async function request<T>(path: string, options: RequestOptions = {}, retried = false): Promise<T> {
  try {
    return await send<T>(buildUrl(path, options.query), options)
  } catch (error) {
    // token 缺失或失效：清空本地凭证后重新登录并重试一次（不递归）
    const unauthorized = error instanceof ApiError && (error.status === 401 || error.status === 403)
    if (unauthorized && !retried) {
      authService.clearToken()
      await authService.login()
      return request<T>(path, options, true)
    }
    throw error
  }
}

export { API_BASE }
