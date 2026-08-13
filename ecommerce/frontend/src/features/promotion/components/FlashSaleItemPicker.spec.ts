import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { productApi } from '@/features/product/api'

import { promotionApi } from '../api'
import FlashSaleItemPicker from './FlashSaleItemPicker.vue'

vi.mock('@/features/product/api', () => ({
  productApi: { categories: vi.fn() },
}))

vi.mock('../api', () => ({
  promotionApi: { flashSaleCatalog: vi.fn() },
}))

const variant = {
  id: '00000000-0000-4000-8000-000000000010',
  sku: 'MOUSE-BLACK',
  name: 'Màu đen',
  sale_price: '900000',
  available_stock: 8,
  product_id: '00000000-0000-4000-8000-000000000001',
  product_name: 'Chuột không dây',
  category_id: '00000000-0000-4000-8000-000000000002',
  category_name: 'Phụ kiện',
  shop_id: 1,
  shop_name: 'Tech Shop',
  primary_image: null,
}

describe('FlashSaleItemPicker', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(productApi.categories).mockResolvedValue({
      data: { success: true, message: 'ok', data: [] },
    } as unknown as Awaited<ReturnType<typeof productApi.categories>>)
    vi.mocked(promotionApi.flashSaleCatalog).mockResolvedValue({
      data: {
        success: true,
        message: 'ok',
        data: [variant],
        meta: { page: 1, page_size: 100, total_items: 1, total_pages: 1 },
      },
    } as unknown as Awaited<ReturnType<typeof promotionApi.flashSaleCatalog>>)
  })

  it('lets an admin add a named product without displaying its UUID', async () => {
    const wrapper = mount(FlashSaleItemPicker, { props: { items: [] } })
    await flushPromises()

    expect(wrapper.text()).toContain('Chuột không dây')
    expect(wrapper.text()).toContain('MOUSE-BLACK')
    expect(wrapper.text()).not.toContain(variant.id)

    const addButton = wrapper.findAll('button').find((button) => button.text() === 'Thêm sản phẩm')
    expect(addButton).toBeDefined()
    await addButton?.trigger('click')

    const emitted = wrapper.emitted('update:items')
    expect(emitted).toHaveLength(1)
    expect(emitted?.[0]?.[0]).toEqual([
      expect.objectContaining({
        variant: variant.id,
        product_name: 'Chuột không dây',
        variant_sku: 'MOUSE-BLACK',
        quota: 8,
      }),
    ])
  })
})
