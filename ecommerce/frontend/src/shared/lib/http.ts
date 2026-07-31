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

export const axiosClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api/v1',
  timeout: 15_000,
  withCredentials: true,
  headers: {
    Accept: 'application/json',
  },
})

// Backward-compatible alias for feature API modules that have not migrated names yet.
export const http = axiosClient

axiosClient.interceptors.request.use((config) => {
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

axiosClient.interceptors.response.use(
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
    refreshPromise ??= authSessionAdapter.refreshAccessToken()

    try {
      const accessToken = await refreshPromise
      config.headers.Authorization = `Bearer ${accessToken}`
      return await axiosClient(config)
    } catch (refreshError) {
      authSessionAdapter.onAuthenticationFailure()
      return Promise.reject(refreshError)
    } finally {
      refreshPromise = null
    }
  },
)
