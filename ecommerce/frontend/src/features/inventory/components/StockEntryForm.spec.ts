import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import StockEntryForm from './StockEntryForm.vue'
import type { InventoryBalance } from '../types'

const inventory: InventoryBalance[] = [
  {
    variant_id: '11111111-1111-4111-8111-111111111111',
    product_id: '22222222-2222-4222-8222-222222222222',
    product_name: 'Áo khoác',
    sku: 'AO-DO-M',
    variant_name: 'Đỏ / M',
    available_stock: 0,
    reserved_stock: 0,
    low_stock_threshold: 5,
    is_low_stock: true,
    updated_at: '2026-07-28T00:00:00Z',
  },
]

describe('StockEntryForm', () => {
  it('validates supplier before emitting', async () => {
    const wrapper = mount(StockEntryForm, { props: { inventory } })

    await wrapper.find('form').trigger('submit')

    expect(wrapper.text()).toContain('Vui lòng nhập tên nhà cung cấp')
    expect(wrapper.emitted('submit')).toBeUndefined()
  })

  it('emits a normalized stock entry payload', async () => {
    const wrapper = mount(StockEntryForm, { props: { inventory } })
    await wrapper.find('input[required]').setValue('Nhà cung cấp A')
    await wrapper.find('select[aria-label="Biến thể"]').setValue(inventory[0]!.variant_id)
    await wrapper.find('input[aria-label="Số lượng nhập"]').setValue(3)
    await wrapper.find('input[aria-label="Giá nhập"]').setValue(45000)

    await wrapper.find('form').trigger('submit')

    expect(wrapper.emitted('submit')?.[0]?.[0]).toEqual({
      supplier_name: 'Nhà cung cấp A',
      note: '',
      items: [
        {
          variant_id: inventory[0]!.variant_id,
          quantity: 3,
          unit_cost: '45000',
        },
      ],
    })
  })
})
