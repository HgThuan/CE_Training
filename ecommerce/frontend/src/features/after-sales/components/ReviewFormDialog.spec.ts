import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { afterSalesApi } from '../api'
import type { Review } from '../types'
import ReviewFormDialog from './ReviewFormDialog.vue'

vi.mock('../api', () => ({
  afterSalesApi: {
    createReview: vi.fn(),
    updateReview: vi.fn(),
  },
}))

const savedReview: Review = {
  id: 'review-id',
  order_item: 'item-id',
  product: 'product-id',
  product_name: 'Sản phẩm thử nghiệm',
  order_code: 'ORD-001',
  customer_name: 'Khách hàng',
  rating: 4,
  content: 'Rất tốt',
  status: 'VISIBLE',
  is_verified_purchase: true,
  editable_until: '2026-08-12T00:00:00Z',
  media: [],
  created_at: '2026-08-05T00:00:00Z',
  updated_at: '2026-08-05T00:00:00Z',
}

function mountDialog(review: Review | null = null) {
  return mount(ReviewFormDialog, {
    props: {
      open: true,
      orderItemId: 'item-id',
      productName: 'Sản phẩm thử nghiệm',
      review,
    },
    global: { stubs: { Teleport: true } },
  })
}

describe('ReviewFormDialog', () => {
  beforeEach(() => vi.clearAllMocks())

  it('creates a verified-purchase review from the customer form', async () => {
    vi.mocked(afterSalesApi.createReview).mockResolvedValue({
      data: { success: true, message: 'ok', data: savedReview },
    } as never)
    const wrapper = mountDialog()

    await wrapper.get('[aria-label="4 sao"]').trigger('click')
    await wrapper.get('#review-content').setValue('Rất tốt')
    await wrapper.get('form').trigger('submit')

    expect(afterSalesApi.createReview).toHaveBeenCalledWith(
      'item-id',
      expect.objectContaining({ rating: 4, content: 'Rất tốt' }),
    )
    expect(wrapper.emitted('saved')?.[0]).toEqual([savedReview])
  })

  it('updates the existing review instead of creating a duplicate', async () => {
    vi.mocked(afterSalesApi.updateReview).mockResolvedValue({
      data: { success: true, message: 'ok', data: { ...savedReview, rating: 5 } },
    } as never)
    const wrapper = mountDialog(savedReview)

    await wrapper.get('[aria-label="5 sao"]').trigger('click')
    await wrapper.get('form').trigger('submit')

    expect(afterSalesApi.updateReview).toHaveBeenCalledWith(
      savedReview.id,
      expect.objectContaining({ rating: 5 }),
    )
    expect(afterSalesApi.createReview).not.toHaveBeenCalled()
  })
})
