import { createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { RouterLinkStub } from '@vue/test-utils'

import HomePage from './HomePage.vue'

describe('HomePage', () => {
  it('renders the auth entry points for a guest', () => {
    const wrapper = mount(HomePage, {
      global: {
        plugins: [createPinia()],
        stubs: { RouterLink: RouterLinkStub },
      },
    })

    expect(wrapper.text()).toContain('Multi-Vendor AI E-commerce')
    expect(wrapper.text()).toContain('Đăng nhập')
    expect(wrapper.text()).toContain('Đăng ký')
  })
})
