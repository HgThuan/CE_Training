import { mount, RouterLinkStub } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { describe, expect, it, vi } from 'vitest'

import type { AuthenticatedUser } from '@/features/auth/types'
import { useAuthStore } from '@/stores/auth'

import RoleHomePage from './RoleHomePage.vue'

vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('vue-router')>()
  return {
    ...actual,
    useRouter: () => ({ replace: vi.fn() }),
  }
})

const admin: AuthenticatedUser = {
  id: 1,
  email: 'admin@example.com',
  role: 'admin',
  is_active: true,
  is_email_verified: true,
  must_change_password: false,
  avatar_url: '',
  full_name: 'Quản trị viên',
  phone: '',
  date_of_birth: null,
  gender: '',
  profile: { permission_level: 'full' },
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

describe('RoleHomePage', () => {
  it('uses user-friendly copy without implementation terminology', () => {
    const pinia = createPinia()
    const authStore = useAuthStore(pinia)
    authStore.user = admin

    const wrapper = mount(RoleHomePage, {
      global: {
        plugins: [pinia],
        stubs: { RouterLink: RouterLinkStub },
      },
    })

    expect(wrapper.text()).toContain('Trang quản lý')
    expect(wrapper.text()).toContain(
      'Chọn một chức năng bên dưới để quản lý tài khoản và thực hiện công việc của bạn.',
    )
    expect(wrapper.text()).not.toMatch(/workspace|JWT|route guard/i)
  })
})
