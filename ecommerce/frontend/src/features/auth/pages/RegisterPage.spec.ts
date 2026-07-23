import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import RegisterPage from './RegisterPage.vue'

const register = vi.fn()
const resendVerification = vi.fn()

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    register,
    resendVerification,
  }),
}))

describe('RegisterPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    register.mockResolvedValue('Đăng ký thành công. Vui lòng kiểm tra email')
    resendVerification.mockResolvedValue('Email xác thực đã được gửi lại')
  })

  it('resends verification to the newly registered email', async () => {
    const wrapper = mount(RegisterPage, {
      global: { stubs: { RouterLink: RouterLinkStub } },
    })
    const form = wrapper.get('form')
    const inputs = form.findAll('input')
    await inputs[0].setValue('New Customer')
    await inputs[1].setValue('new.customer@gmail.com')
    await inputs[2].setValue('StrongPass!234')
    await inputs[3].setValue('StrongPass!234')
    await form.trigger('submit')
    await flushPromises()

    const resendButton = wrapper
      .findAll('button')
      .find((button) => button.text().includes('Gửi lại xác thực'))
    expect(resendButton).toBeDefined()

    await resendButton?.trigger('click')
    await flushPromises()

    expect(resendVerification).toHaveBeenCalledWith('new.customer@gmail.com')
    expect(wrapper.text()).toContain('Email xác thực đã được gửi lại')
  })
})
