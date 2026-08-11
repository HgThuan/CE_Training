import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { SellerProductListItem } from '@/features/product/types'

import { sellerProductApi } from '../product-api'
import ProductListPage from './ProductListPage.vue'

vi.mock('../product-api', () => ({
  sellerProductApi: {
    list: vi.fn(),
    submit: vi.fn(),
    delete: vi.fn(),
  },
}))

const hiddenProduct: SellerProductListItem = {
  id: 'hidden-product-id',
  name: 'Sản phẩm bị ẩn',
  slug: 'san-pham-bi-an',
  status: 'hidden',
  rejection_reason: 'Hình ảnh sản phẩm vi phạm chính sách',
  thumbnail: null,
  min_price: '100000',
  max_price: '100000',
  created_at: '2026-08-11T00:00:00Z',
}

describe('Seller ProductListPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(sellerProductApi.list).mockResolvedValue({
      data: {
        success: true,
        message: 'ok',
        data: [hiddenProduct],
        meta: { page: 1, page_size: 20, total_items: 1, total_pages: 1 },
      },
    } as Awaited<ReturnType<typeof sellerProductApi.list>>)
  })

  it('shows the moderation reason for a hidden product', async () => {
    const wrapper = mount(ProductListPage, {
      global: {
        stubs: {
          RouterLink: { template: '<a><slot /></a>' },
          FormMessage: { template: '<p />' },
        },
      },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('Đã ẩn')
    expect(wrapper.text()).toContain('Lý do ẩn: Hình ảnh sản phẩm vi phạm chính sách')
  })
})
