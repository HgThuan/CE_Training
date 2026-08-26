import { mount, RouterLinkStub } from '@vue/test-utils'
import { nextTick } from 'vue'
import { afterEach, beforeEach, vi } from 'vitest'

import { useCartToast } from '../composables/useCartToast'
import CartToast from './CartToast.vue'

describe('CartToast', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    useCartToast().hide()
  })

  afterEach(() => {
    useCartToast().hide()
    vi.useRealTimers()
  })

  it('shows added item details and dismisses automatically', async () => {
    const wrapper = mount(CartToast, {
      global: { stubs: { RouterLink: RouterLinkStub } },
    })

    useCartToast().show({
      status: 'success',
      item: {
        product_name: 'Bàn phím cơ',
        variant_name: 'Red Switch',
        quantity: 2,
        price: '2590000',
        image: null,
      },
    })
    await nextTick()

    const toast = wrapper.get('[data-testid="cart-toast"]')
    expect(toast.attributes('role')).toBe('status')
    expect(toast.attributes('aria-live')).toBe('polite')
    expect(toast.text()).toContain('Bàn phím cơ')
    expect(toast.text()).toContain('Red Switch')
    expect(toast.text()).toContain('Số lượng: 2')
    expect(toast.text()).toContain('2.590.000')

    await vi.advanceTimersByTimeAsync(5000)
    await nextTick()
    expect(wrapper.find('[data-testid="cart-toast"]').exists()).toBe(false)
  })

  it('announces cart errors assertively', async () => {
    const wrapper = mount(CartToast, {
      global: { stubs: { RouterLink: RouterLinkStub } },
    })

    useCartToast().show({ status: 'error', message: 'Sản phẩm đã hết hàng' })
    await nextTick()

    const toast = wrapper.get('[data-testid="cart-toast"]')
    expect(toast.attributes('role')).toBe('alert')
    expect(toast.attributes('aria-live')).toBe('assertive')
    expect(toast.text()).toContain('Sản phẩm đã hết hàng')
  })
})
