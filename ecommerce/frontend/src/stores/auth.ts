import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { authApi } from '@/features/auth/api'
import type {
  AuthenticatedUser,
  ChangePasswordPayload,
  LoginPayload,
  ProfilePayload,
  RegisterPayload,
  ResetPasswordPayload,
} from '@/features/auth/types'
import { setAuthSessionAdapter } from '@/shared/lib/http'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(null)
  const user = ref<AuthenticatedUser | null>(null)
  const initialized = ref(false)

  const isAuthenticated = computed(() => Boolean(accessToken.value && user.value))

  function clearSession(): void {
    accessToken.value = null
    user.value = null
  }

  function applySession(data: { access: string; user: AuthenticatedUser }): string {
    accessToken.value = data.access
    user.value = data.user
    return data.access
  }

  async function refreshAccessToken(): Promise<string> {
    const response = await authApi.refresh()
    return applySession(response.data.data)
  }

  function bindHttpClient(): void {
    setAuthSessionAdapter({
      getAccessToken: () => accessToken.value,
      refreshAccessToken,
      onAuthenticationFailure: clearSession,
    })
  }

  async function restoreSession(): Promise<void> {
    if (initialized.value) return
    try {
      const response = await authApi.session()
      if (response.data.data) {
        applySession(response.data.data)
      } else {
        clearSession()
      }
    } catch {
      clearSession()
    } finally {
      initialized.value = true
    }
  }

  async function login(payload: LoginPayload): Promise<void> {
    const response = await authApi.login(payload)
    applySession(response.data.data)
    window.dispatchEvent(new CustomEvent('auth:authenticated'))
  }

  async function logout(): Promise<void> {
    try {
      if (accessToken.value) await authApi.logout()
    } finally {
      clearSession()
    }
  }

  async function register(payload: RegisterPayload): Promise<string> {
    const response = await authApi.register(payload)
    return response.data.message
  }

  async function verifyEmail(token: string): Promise<string> {
    const response = await authApi.verifyEmail(token)
    return response.data.message
  }

  async function resendVerification(email: string): Promise<string> {
    const response = await authApi.resendVerification(email)
    return response.data.message
  }

  async function forgotPassword(email: string): Promise<string> {
    const response = await authApi.forgotPassword(email)
    return response.data.message
  }

  async function resetPassword(payload: ResetPasswordPayload): Promise<string> {
    const response = await authApi.resetPassword(payload)
    return response.data.message
  }

  async function updateProfile(payload: ProfilePayload): Promise<string> {
    const response = await authApi.updateProfile(payload)
    user.value = response.data.data
    return response.data.message
  }

  async function uploadAvatar(avatar: Blob): Promise<string> {
    const response = await authApi.uploadAvatar(avatar)
    user.value = response.data.data
    return response.data.message
  }

  async function changePassword(payload: ChangePasswordPayload): Promise<string> {
    const response = await authApi.changePassword(payload)
    clearSession()
    return response.data.message
  }

  return {
    accessToken,
    user,
    initialized,
    isAuthenticated,
    bindHttpClient,
    restoreSession,
    refreshAccessToken,
    login,
    logout,
    register,
    verifyEmail,
    resendVerification,
    forgotPassword,
    resetPassword,
    updateProfile,
    uploadAvatar,
    changePassword,
    clearSession,
  }
})
