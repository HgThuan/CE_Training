import { beforeEach, vi } from 'vitest'

import { http } from '@/shared/lib/http'

import { trackRecommendationClick, trackRecommendationImpression } from './recommendationTracking'

vi.mock('@/shared/lib/http', () => ({
  http: {
    post: vi.fn(),
  },
}))

describe('recommendation tracking', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.localStorage.clear()
    vi.mocked(http.post).mockResolvedValue({} as never)
  })

  it('deduplicates an impression for the same recommendation and product', async () => {
    trackRecommendationImpression('recommendation-1', 'product-1', 'home', 0)
    trackRecommendationImpression('recommendation-1', 'product-1', 'home', 0)
    await Promise.resolve()

    expect(http.post).toHaveBeenCalledOnce()
    expect(http.post).toHaveBeenCalledWith(
      '/ai/recommendation-events/',
      expect.objectContaining({
        recommendation_id: 'recommendation-1',
        product_id: 'product-1',
        event_type: 'impression',
        source: 'home',
        position: 0,
      }),
    )
  })

  it('does not retry the same optional impression when telemetry fails', async () => {
    vi.mocked(http.post).mockRejectedValueOnce(new Error('rate limited'))

    trackRecommendationImpression('recommendation-2', 'product-2', 'product', 1)
    trackRecommendationImpression('recommendation-2', 'product-2', 'product', 1)
    await Promise.resolve()

    expect(http.post).toHaveBeenCalledOnce()
  })

  it('stores click attribution and records the click independently', async () => {
    trackRecommendationClick('recommendation-3', 'product-3', 'similar', 2)
    await Promise.resolve()

    expect(
      JSON.parse(window.localStorage.getItem('mercato.recommendation.attribution:product-3')!),
    ).toEqual(
      expect.objectContaining({
        recommendation_id: 'recommendation-3',
        product_id: 'product-3',
        source: 'similar',
        position: 2,
      }),
    )
    expect(http.post).toHaveBeenCalledWith(
      '/ai/recommendation-events/',
      expect.objectContaining({ event_type: 'click' }),
    )
  })
})
