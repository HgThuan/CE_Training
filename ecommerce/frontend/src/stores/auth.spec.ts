import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { authApi } from '@/features/auth/api'
import type { AuthenticatedUser } from '@/features/auth/types'

import { useAuthStore } from './auth'

vi.mock('@/features/auth/api', () => ({
  authApi: {
    login: vi.fn(),
    logout: vi.fn(),
    session: vi.fn(),
    refresh: vi.fn(),
    register: vi.fn(),
    verifyEmail: vi.fn(),
    forgotPassword: vi.fn(),
    resetPassword: vi.fn(),
    updateProfile: vi.fn(),
    uploadAvatar: vi.fn(),
    changePassword: vi.fn(),
  },
}))

const customer: AuthenticatedUser = {
  id: 1,
  email: 'customer@example.com',
  role: 'customer',
  is_active: true,
  is_email_verified: true,
  must_change_password: false,
  avatar_url: '',
  full_name: 'Customer',
  phone: '',
  date_of_birth: null,
  gender: '',
  profile: { loyalty_points: 0, wallet_balance: '0' },
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('keeps access token in store state and clears it on logout', async () => {
    vi.mocked(authApi.login).mockResolvedValue({
      data: {
        success: true,
        message: 'ok',
        data: { access: 'access-token', access_expires_in: 900, user: customer },
      },
    } as Awaited<ReturnType<typeof authApi.login>>)
    vi.mocked(authApi.logout).mockResolvedValue({
      data: { success: true, message: 'ok', data: null },
    } as Awaited<ReturnType<typeof authApi.logout>>)
    const store = useAuthStore()

    await store.login({ email: customer.email, password: 'password' })
    expect(store.accessToken).toBe('access-token')
    expect(store.isAuthenticated).toBe(true)

    await store.logout()
    expect(store.accessToken).toBeNull()
    expect(store.user).toBeNull()
  })

  it('keeps a guest bootstrap as a successful unauthenticated state', async () => {
    vi.mocked(authApi.session).mockResolvedValue({
      data: { success: true, message: 'Không có phiên đăng nhập', data: null },
    } as Awaited<ReturnType<typeof authApi.session>>)
    const store = useAuthStore()

    await store.restoreSession()

    expect(store.initialized).toBe(true)
    expect(store.isAuthenticated).toBe(false)
    expect(authApi.refresh).not.toHaveBeenCalled()
  })

  it('restores a valid session during bootstrap', async () => {
    vi.mocked(authApi.session).mockResolvedValue({
      data: {
        success: true,
        message: 'Khôi phục phiên đăng nhập thành công',
        data: { access: 'restored-token', access_expires_in: 900, user: customer },
      },
    } as Awaited<ReturnType<typeof authApi.session>>)
    const store = useAuthStore()

    await store.restoreSession()

    expect(store.accessToken).toBe('restored-token')
    expect(store.user).toEqual(customer)
    expect(store.isAuthenticated).toBe(true)
  })

  it('uploads a cropped avatar and refreshes the user in memory', async () => {
    const updatedCustomer = { ...customer, avatar_url: '/media/avatars/1/avatar.jpg' }
    vi.mocked(authApi.uploadAvatar).mockResolvedValue({
      data: {
        success: true,
        message: 'Cập nhật ảnh đại diện thành công',
        data: updatedCustomer,
      },
    } as Awaited<ReturnType<typeof authApi.uploadAvatar>>)
    const store = useAuthStore()
    const avatar = new Blob(['cropped-image'], { type: 'image/jpeg' })

    const message = await store.uploadAvatar(avatar)

    expect(authApi.uploadAvatar).toHaveBeenCalledWith(avatar)
    expect(store.user?.avatar_url).toBe('/media/avatars/1/avatar.jpg')
    expect(message).toBe('Cập nhật ảnh đại diện thành công')
  })
})
