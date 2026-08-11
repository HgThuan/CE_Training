import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { AdminProductListItem } from '@/features/product/types'

import { adminCatalogApi } from '../api'
import ProductModerationPage from './ProductModerationPage.vue'

vi.mock('../api', () => ({
  adminCatalogApi: {
    products: vi.fn(),
    approveProduct: vi.fn(),
    rejectProduct: vi.fn(),
    hideProduct: vi.fn(),
    deleteProduct: vi.fn(),
  },
}))

const product = (status: AdminProductListItem['status']): AdminProductListItem => ({
  id: `${status}-id`,
  name: `Sản phẩm ${status}`,
  slug: `san-pham-${status}`,
  status,
  rejection_reason: null,
  thumbnail: null,
  min_price: '100000',
  max_price: '100000',
  category: { id: 'category-id', name: 'Thời trang', slug: 'thoi-trang' },
  shop_name: 'Shop kiểm thử',
  seller_id: 10,
  seller_email: 'seller@example.com',
  seller_name: 'Seller Test',
  created_at: '2026-08-11T00:00:00Z',
})

describe('ProductModerationPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.mocked(adminCatalogApi.products).mockResolvedValue({
      data: {
        success: true,
        message: 'ok',
        data: [product('approved'), product('hidden')],
        meta: { page: 1, page_size: 20, total_items: 2, total_pages: 1 },
      },
    } as Awaited<ReturnType<typeof adminCatalogApi.products>>)
    vi.mocked(adminCatalogApi.hideProduct).mockResolvedValue({
      data: { success: true, message: 'Đã ẩn', data: product('hidden') },
    } as Awaited<ReturnType<typeof adminCatalogApi.hideProduct>>)
    vi.mocked(adminCatalogApi.deleteProduct).mockResolvedValue({
      data: {
        success: true,
        message: 'Đã xóa',
        data: { id: 'hidden-id', is_deleted: true },
      },
    } as Awaited<ReturnType<typeof adminCatalogApi.deleteProduct>>)
  })

  it('loads the moderation catalog and exposes valid ADM-14 actions', async () => {
    const wrapper = mount(ProductModerationPage, {
      global: {
        stubs: {
          FormMessage: { template: '<p />' },
        },
      },
    })
    await flushPromises()

    expect(adminCatalogApi.products).toHaveBeenCalledWith({
      page: 1,
      page_size: 20,
      status: 'pending_review',
      search: undefined,
    })

    const hideButton = wrapper
      .findAll('button')
      .find((button) => button.text().includes('Ẩn vi phạm'))
    expect(hideButton).toBeDefined()
    await hideButton!.trigger('click')
    await flushPromises()
    expect(adminCatalogApi.hideProduct).toHaveBeenCalledWith('approved-id')

    const deleteButton = wrapper
      .findAll('button')
      .find((button) => button.text().includes('Xóa mềm'))
    expect(deleteButton).toBeDefined()
    await deleteButton!.trigger('click')
    await flushPromises()
    expect(adminCatalogApi.deleteProduct).toHaveBeenCalledWith('hidden-id')
  })
})
