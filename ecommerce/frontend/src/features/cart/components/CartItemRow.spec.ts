import { mount, RouterLinkStub } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { CartItem } from '../types'
import CartItemRow from './CartItemRow.vue'

const item: CartItem = {
  id: 'item-1',
  variant_id: 'variant-1',
  variant_sku: 'SKU-1',
  variant_name: 'Đen',
  product_id: 'product-1',
  product_name: 'Tai nghe',
  product_slug: 'tai-nghe',
  primary_image: null,
  quantity: 1,
  is_selected: true,
  unit_price_snapshot: '100000',
  current_price: '100000',
  regular_price: '100000',
  is_flash_sale: false,
  flash_sale_ends_at: null,
  remaining_flash_quota: null,
  line_total: '100000',
  available_stock: 5,
  price_changed: false,
  is_valid: true,
}

describe('CartItemRow', () => {
  afterEach(() => vi.useRealTimers())

  it('emits the increased quantity after the debounce window', async () => {
    vi.useFakeTimers()
    const wrapper = mount(CartItemRow, {
      props: { item },
      global: { stubs: { RouterLink: RouterLinkStub } },
    })

    await wrapper.get('input[type="number"]').setValue('2')
    vi.advanceTimersByTime(350)

    expect(wrapper.emitted('update')).toEqual([[item, { quantity: 2 }]])
    wrapper.unmount()
  })
})
