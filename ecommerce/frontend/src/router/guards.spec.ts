import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { authApi } from '@/features/auth/api'
import type { AuthenticatedUser } from '@/features/auth/types'
import { useAuthStore } from '@/stores/auth'

import { registerRoleGuards } from './guards'

vi.mock('@/features/auth/api', () => ({
  authApi: {
    login: vi.fn(),
    session: vi.fn(),
    refresh: vi.fn(),
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
  profile: null,
  created_at: '',
  updated_at: '',
}

function buildRouter() {
  const component = { template: '<div />' }
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/auth/login', component },
      { path: '/account/profile', component, meta: { requiresAuth: true } },
      { path: '/admin', component, meta: { requiresAuth: true, roles: ['admin'] } },
    ],
  })
  registerRoleGuards(router)
  return router
}

describe('role guards', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('redirects guests to login with the original destination', async () => {
    vi.mocked(authApi.session).mockResolvedValue({
      data: { success: true, message: 'Không có phiên đăng nhập', data: null },
    } as Awaited<ReturnType<typeof authApi.session>>)
    const router = buildRouter()

    await router.push('/admin')
    await router.isReady()

    expect(router.currentRoute.value.path).toBe('/auth/login')
    expect(router.currentRoute.value.query.redirect).toBe('/admin')
  })

  it('redirects a customer away from an admin-only route', async () => {
    vi.mocked(authApi.login).mockResolvedValue({
      data: {
        success: true,
        message: 'ok',
        data: { access: 'token', access_expires_in: 900, user: customer },
      },
    } as Awaited<ReturnType<typeof authApi.login>>)
    const authStore = useAuthStore()
    await authStore.login({ email: customer.email, password: 'password' })
    authStore.initialized = true
    const router = buildRouter()

    await router.push('/admin')
    await router.isReady()

    expect(router.currentRoute.value.path).toBe('/account/profile')
  })
})
