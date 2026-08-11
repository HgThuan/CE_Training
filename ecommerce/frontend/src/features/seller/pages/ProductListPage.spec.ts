import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { SellerProductListItem } from '@/features/product/types'
import { confirmDialog } from '@/shared/composables/useAppDialog'

import { sellerProductApi } from '../product-api'
import ProductListPage from './ProductListPage.vue'

vi.mock('../product-api', () => ({
  sellerProductApi: {
    list: vi.fn(),
    submit: vi.fn(),
    suspend: vi.fn(),
    restore: vi.fn(),
    delete: vi.fn(),
  },
}))

vi.mock('@/shared/composables/useAppDialog', () => ({
  confirmDialog: vi.fn(),
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

const approvedProduct: SellerProductListItem = {
  ...hiddenProduct,
  id: 'approved-product-id',
  name: 'Sản phẩm đang bán',
  slug: 'san-pham-dang-ban',
  status: 'approved',
  rejection_reason: null,
}

const suspendedProduct: SellerProductListItem = {
  ...hiddenProduct,
  id: 'suspended-product-id',
  name: 'Sản phẩm tạm ngưng',
  slug: 'san-pham-tam-ngung',
  status: 'suspended',
  rejection_reason: null,
}

describe('Seller ProductListPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(confirmDialog).mockResolvedValue(true)
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

  it('lets the seller suspend and restore product availability', async () => {
    vi.mocked(sellerProductApi.list).mockResolvedValue({
      data: {
        success: true,
        message: 'ok',
        data: [approvedProduct, suspendedProduct],
        meta: { page: 1, page_size: 20, total_items: 2, total_pages: 1 },
      },
    } as Awaited<ReturnType<typeof sellerProductApi.list>>)
    vi.mocked(sellerProductApi.suspend).mockResolvedValue({
      data: { success: true, message: 'Đã tạm ngưng bán sản phẩm', data: suspendedProduct },
    } as unknown as Awaited<ReturnType<typeof sellerProductApi.suspend>>)
    vi.mocked(sellerProductApi.restore).mockResolvedValue({
      data: { success: true, message: 'Đã mở bán lại sản phẩm', data: approvedProduct },
    } as unknown as Awaited<ReturnType<typeof sellerProductApi.restore>>)
    const wrapper = mount(ProductListPage, {
      global: {
        stubs: {
          RouterLink: { template: '<a><slot /></a>' },
          FormMessage: { template: '<p />' },
        },
      },
    })
    await flushPromises()

    const suspendButton = wrapper
      .findAll('button')
      .find((button) => button.text() === 'Tạm ngưng bán')
    expect(suspendButton).toBeDefined()
    await suspendButton!.trigger('click')
    await flushPromises()
    expect(sellerProductApi.suspend).toHaveBeenCalledWith('approved-product-id')

    const restoreButton = wrapper.findAll('button').find((button) => button.text() === 'Mở bán lại')
    expect(restoreButton).toBeDefined()
    await restoreButton!.trigger('click')
    await flushPromises()
    expect(sellerProductApi.restore).toHaveBeenCalledWith('suspended-product-id')
  })
})
