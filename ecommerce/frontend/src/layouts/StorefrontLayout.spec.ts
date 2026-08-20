import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'

import StorefrontLayout from './StorefrontLayout.vue'

describe('StorefrontLayout', () => {
  it('opens the mobile navigation and closes it after a route change', async () => {
    const child = { template: '<main />' }
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', component: child },
        { path: '/products', component: child },
        { path: '/search', component: child },
      ],
    })
    await router.push('/')
    await router.isReady()
    const wrapper = mount(StorefrontLayout, {
      global: {
        plugins: [createPinia(), router],
        stubs: {
          ChatWidget: true,
          ProductCompareBar: true,
          SearchBar: { template: '<form role="search" />' },
          RouterView: true,
        },
      },
    })

    await wrapper.get('button[aria-label="Mở menu"]').trigger('click')
    expect(wrapper.find('#storefront-mobile-menu').exists()).toBe(true)
    expect(wrapper.text()).toContain('Đăng ký')

    await router.push('/products')
    await flushPromises()

    expect(wrapper.find('#storefront-mobile-menu').exists()).toBe(false)
  })
})
