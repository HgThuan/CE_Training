import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'

interface RetryableRequestConfig extends InternalAxiosRequestConfig {
  _retry?: boolean
}

interface AuthSessionAdapter {
  getAccessToken: () => string | null
  refreshAccessToken: () => Promise<string>
  onAuthenticationFailure: () => void
}

let authSessionAdapter: AuthSessionAdapter | null = null
let refreshPromise: Promise<string> | null = null

export function setAuthSessionAdapter(adapter: AuthSessionAdapter): void {
  authSessionAdapter = adapter
}

export function refreshAuthSession(): Promise<string> {
  if (!authSessionAdapter) {
    return Promise.reject(new Error('Auth session adapter is not initialized'))
  }

  if (!refreshPromise) {
    const adapter = authSessionAdapter
    refreshPromise = adapter
      .refreshAccessToken()
      .catch((error: unknown) => {
        adapter.onAuthenticationFailure()
        throw error
      })
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api/v1',
  timeout: 15_000,
  withCredentials: true,
  headers: {
    Accept: 'application/json',
  },
})

http.interceptors.request.use((config) => {
  const accessToken = authSessionAdapter?.getAccessToken()
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
})

const publicAuthPaths = [
  '/auth/login/',
  '/auth/register/',
  '/auth/session/',
  '/auth/refresh/',
  '/auth/verify-email/',
  '/auth/resend-verification/',
  '/auth/forgot-password/',
  '/auth/reset-password/',
]

http.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as RetryableRequestConfig | undefined
    const isPublicAuthRequest = publicAuthPaths.some((path) => config?.url?.includes(path))
    if (
      error.response?.status !== 401 ||
      !config ||
      config._retry ||
      isPublicAuthRequest ||
      !authSessionAdapter
    ) {
      return Promise.reject(error)
    }

    config._retry = true
    try {
      const accessToken = await refreshAuthSession()
      config.headers.Authorization = `Bearer ${accessToken}`
      return await http(config)
    } catch (refreshError) {
      return Promise.reject(refreshError)
    }
  },
)
