import { beforeEach, vi } from 'vitest'

import { http } from '@/shared/lib/http'

import { sellerProductApi } from './product-api'

vi.mock('@/shared/lib/http', () => ({
  http: {
    post: vi.fn(),
  },
}))

describe('seller product AI API', () => {
  beforeEach(() => vi.clearAllMocks())

  it('posts the name and keywords to the listing endpoint', () => {
    sellerProductApi.generateListing('Áo sơ mi', ['cotton', 'công sở'])

    expect(http.post).toHaveBeenCalledWith('/seller/products/generate-listing', {
      name: 'Áo sơ mi',
      keywords: ['cotton', 'công sở'],
    })
  })
})
