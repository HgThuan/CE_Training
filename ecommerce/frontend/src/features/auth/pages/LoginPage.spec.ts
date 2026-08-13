import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import LoginPage from './LoginPage.vue'

const login = vi.fn()
const replace = vi.fn()

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({ login, user: { role: 'customer' } }),
}))
vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('vue-router')>()
  return {
    ...actual,
    useRoute: () => ({ query: {} }),
    useRouter: () => ({ replace }),
  }
})

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    login.mockResolvedValue(undefined)
  })

  it('shows inline errors and does not submit invalid values', async () => {
    const wrapper = mount(LoginPage, { global: { stubs: { RouterLink: RouterLinkStub } } })
    await wrapper.get('input[type="email"]').setValue('email-sai')
    await wrapper.get('form').trigger('submit')

    expect(wrapper.text()).toContain('Email chưa đúng định dạng.')
    expect(wrapper.text()).toContain('Vui lòng nhập mật khẩu.')
    expect(login).not.toHaveBeenCalled()
  })

  it('toggles password visibility and submits valid credentials once', async () => {
    const wrapper = mount(LoginPage, { global: { stubs: { RouterLink: RouterLinkStub } } })
    await wrapper.get('input[type="email"]').setValue('customer@example.com')
    const password = wrapper.get('#login-password')
    await password.setValue('StrongPass!234')
    await wrapper.get('button[aria-label="Hiện mật khẩu"]').trigger('click')
    expect(password.attributes('type')).toBe('text')

    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(login).toHaveBeenCalledOnce()
    expect(replace).toHaveBeenCalledWith('/account/profile')
  })
})
