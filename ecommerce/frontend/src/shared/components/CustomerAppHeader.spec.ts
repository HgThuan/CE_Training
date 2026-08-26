import { createPinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import { vi } from 'vitest'

import { useCartStore } from '@/features/cart/store'

import CustomerAppHeader from './CustomerAppHeader.vue'

const cart = {
  id: 'cart-1',
  total_items: 3,
  total_selected_items: 3,
  shops: [],
  subtotal: '0',
  updated_at: '2026-08-26T00:00:00Z',
}

describe('CustomerAppHeader cart feedback', () => {
  it('loads the cart and keeps desktop and mobile counts reactive', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', component: { template: '<main />' } },
        { path: '/cart', component: { template: '<main />' } },
        { path: '/:pathMatch(.*)*', component: { template: '<main />' } },
      ],
    })
    await router.push('/')
    await router.isReady()

    const pinia = createPinia()
    const cartStore = useCartStore(pinia)
    cartStore.cart = { ...cart }
    const load = vi.spyOn(cartStore, 'load').mockResolvedValue()

    const wrapper = mount(CustomerAppHeader, {
      global: {
        plugins: [pinia, router],
        stubs: {
          CartToast: true,
          NotificationBell: true,
          SearchBar: { template: '<form role="search" />' },
        },
      },
    })

    expect(load).toHaveBeenCalledOnce()
    expect(wrapper.get('[data-testid="desktop-cart-count"]').text()).toBe('3')
    expect(wrapper.get('[data-testid="mobile-cart-count"]').text()).toBe('3')
    expect(wrapper.get('a[href="/cart"]').attributes('aria-label')).toBe('Giỏ hàng, 3 sản phẩm')

    cartStore.cart = { ...cart, total_items: 105 }
    await nextTick()

    expect(wrapper.get('[data-testid="desktop-cart-count"]').text()).toBe('99+')
    expect(wrapper.get('[data-testid="mobile-cart-count"]').text()).toBe('99+')
    expect(wrapper.get('a[href="/cart"]').classes()).toContain('scale-110')
    wrapper.unmount()
  })
})
