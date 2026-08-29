import Taro from '@tarojs/taro'
import { storage } from './storage'

const TOKEN_KEY = 'auth-token'
const USER_KEY = 'auth-user'
const API_BASE = (process.env.TARO_APP_API_BASE || 'http://127.0.0.1:8000/api/v1').replace(/\/$/, '')

interface AuthUser {
  id: string
  provider: string
  subject: string
  display_name: string | null
}

interface TokenResponse {
  access_token: string
  user: AuthUser
}

async function postLogin(path: string, data: unknown): Promise<TokenResponse> {
  const response = await Taro.request<TokenResponse | { detail?: string }>({
    url: `${API_BASE}${path}`,
    method: 'POST',
    data,
    timeout: 12000,
    header: { 'content-type': 'application/json' },
  })
  if (response.statusCode < 200 || response.statusCode >= 300 || !('access_token' in response.data)) {
    const message = 'detail' in response.data ? response.data.detail : undefined
    throw new Error(message || '登录失败')
  }
  return response.data
}

export const authService = {
  getToken(): string {
    return storage.get<string>(TOKEN_KEY, '') || process.env.TARO_APP_DEV_TOKEN || ''
  },
  getUser(): AuthUser | null {
    return storage.get<AuthUser | null>(USER_KEY, null)
  },
  setSession(result: TokenResponse) {
    storage.set(TOKEN_KEY, result.access_token.trim())
    storage.set(USER_KEY, result.user)
  },
  setToken(token: string) {
    storage.set(TOKEN_KEY, token.trim())
  },
  clearToken() {
    storage.remove(TOKEN_KEY)
    storage.remove(USER_KEY)
  },
  isLocalDev(): boolean {
    return process.env.NODE_ENV === 'development'
  },
  async login(): Promise<AuthUser> {
    if (process.env.NODE_ENV === 'development') {
      const result = await postLogin('/auth/dev-login', {
        subject: 'miniapp-dev',
        display_name: 'Miniapp Developer',
      })
      this.setSession(result)
      return result.user
    }
    const login = await Taro.login()
    if (!login.code) throw new Error('微信登录未返回 code')
    const result = await postLogin('/auth/wechat/login', { code: login.code })
    this.setSession(result)
    return result.user
  },
  async ensureAuthenticated(): Promise<void> {
    if (!this.getToken()) await this.login()
  },
}
