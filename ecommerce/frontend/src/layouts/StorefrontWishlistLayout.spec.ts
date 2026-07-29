import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'

import type { AuthenticatedUser } from '@/features/auth/types'
import { useAuthStore } from '@/stores/auth'

import StorefrontLayout from './StorefrontLayout.vue'

const customer: AuthenticatedUser = {
  id: 10,
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

describe('StorefrontLayout customer navigation', () => {
  it('shows wishlist links and closes the mobile menu with Escape', async () => {
    const component = { template: '<main />' }
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', component },
        { path: '/wishlist', component },
        { path: '/products', component },
        { path: '/account/profile', component },
      ],
    })
    await router.push('/')
    await router.isReady()
    const pinia = createPinia()
    const authStore = useAuthStore(pinia)
    authStore.user = customer
    authStore.accessToken = 'token'
    const wrapper = mount(StorefrontLayout, {
      attachTo: document.body,
      global: {
        plugins: [pinia, router],
        stubs: {
          SearchBar: { template: '<form role="search" />' },
          RouterView: true,
        },
      },
    })

    expect(wrapper.findAll('a[href="/wishlist"]')).toHaveLength(1)
    const menuButton = wrapper.get('button[aria-label="Mở menu"]')
    await menuButton.trigger('click')
    expect(wrapper.findAll('a[href="/wishlist"]')).toHaveLength(2)

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await flushPromises()

    expect(wrapper.find('#storefront-mobile-menu').exists()).toBe(false)
    expect(document.activeElement).toBe(menuButton.element)
    wrapper.unmount()
  })
})
