import { beforeEach, vi } from 'vitest'

import { http } from '@/shared/lib/http'

import { productApi } from './api'

vi.mock('@/shared/lib/http', () => ({
  http: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

describe('product recommendation API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(http.get).mockResolvedValue({} as never)
  })

  it('calls the product-scoped similar endpoint', () => {
    productApi.similar('product-id')

    expect(http.get).toHaveBeenCalledWith('/products/product-id/similar/')
  })

  it('serializes browsing history as one CSV query value for anchored recommendations', () => {
    productApi.recommendations('product-id', ['history-1', 'history-2'])

    expect(http.get).toHaveBeenCalledWith('/products/product-id/recommendations/', {
      params: {
        browsing_history: 'history-1,history-2',
      },
    })
    const requestConfig = vi.mocked(http.get).mock.calls[0]?.[1]
    expect(Array.isArray(requestConfig?.params?.browsing_history)).toBe(false)
  })

  it('serializes browsing history for home recommendations without sending an Axios array', () => {
    productApi.homeRecommendations(['history-2', 'history-1'])

    expect(http.get).toHaveBeenCalledWith('/ai/recommendations/', {
      params: {
        browsing_history: 'history-2,history-1',
      },
    })
  })

  it('omits the browsing_history query when there is no history', () => {
    productApi.recommendations('product-id')
    productApi.homeRecommendations()

    expect(http.get).toHaveBeenNthCalledWith(1, '/products/product-id/recommendations/', {
      params: {},
    })
    expect(http.get).toHaveBeenNthCalledWith(2, '/ai/recommendations/', {
      params: {},
    })
  })

  it('calls the AI summary endpoints without trailing slashes', () => {
    productApi.aiReviewSummary('product-id')
    productApi.aiSummary('product-id')

    expect(http.get).toHaveBeenNthCalledWith(1, '/ai/products/product-id/ai-review-summary')
    expect(http.get).toHaveBeenNthCalledWith(2, '/ai/products/product-id/ai-summary')
  })

  it('posts selected product IDs to the comparison endpoint', () => {
    productApi.compareProducts(['product-1', 'product-2'])

    expect(http.post).toHaveBeenCalledWith('/products/compare', {
      product_ids: ['product-1', 'product-2'],
    })
  })
})
