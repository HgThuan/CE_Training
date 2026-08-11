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
    unhideProduct: vi.fn(),
    deleteProduct: vi.fn(),
  },
}))

const product = (status: AdminProductListItem['status']): AdminProductListItem => ({
  id: `${status}-id`,
  name: `Sản phẩm ${status}`,
  slug: `san-pham-${status}`,
  status,
  rejection_reason: status === 'hidden' ? 'Hình ảnh vi phạm chính sách' : null,
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
    vi.mocked(adminCatalogApi.unhideProduct).mockResolvedValue({
      data: { success: true, message: 'Đã bỏ ẩn', data: product('approved') },
    } as Awaited<ReturnType<typeof adminCatalogApi.unhideProduct>>)
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
    const hideForm = wrapper
      .findAll('form')
      .find((form) => form.text().includes('Ẩn sản phẩm vi phạm'))
    expect(hideForm).toBeDefined()
    await hideForm!.find('textarea').setValue('Hình ảnh vi phạm chính sách')
    await hideForm!.trigger('submit')
    await flushPromises()
    expect(adminCatalogApi.hideProduct).toHaveBeenCalledWith(
      'approved-id',
      'Hình ảnh vi phạm chính sách',
    )

    expect(wrapper.text()).toContain('Lý do ẩn: Hình ảnh vi phạm chính sách')
    const unhideButton = wrapper.findAll('button').find((button) => button.text().includes('Bỏ ẩn'))
    expect(unhideButton).toBeDefined()
    await unhideButton!.trigger('click')
    await flushPromises()
    expect(adminCatalogApi.unhideProduct).toHaveBeenCalledWith('hidden-id')

    const deleteButton = wrapper
      .findAll('button')
      .find((button) => button.text().includes('Xóa mềm'))
    expect(deleteButton).toBeDefined()
    await deleteButton!.trigger('click')
    await flushPromises()
    expect(adminCatalogApi.deleteProduct).toHaveBeenCalledWith('hidden-id')
  })
})
