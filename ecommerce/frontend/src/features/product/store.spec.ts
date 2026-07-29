import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, vi } from 'vitest'

import { productApi } from './api'
import { useProductStore } from './store'
import type { PublicProductDetail } from './types'

vi.mock('./api', () => ({
  productApi: {
    brands: vi.fn(),
    categories: vi.fn(),
    detail: vi.fn(),
    list: vi.fn(),
  },
}))

function detail(id: string, name: string): PublicProductDetail {
  return {
    id,
    name,
    slug: id,
    short_description: null,
    description: null,
    category: { id: 'category-1', name: 'Điện thoại', slug: 'dien-thoai' },
    brand: null,
    shop: {
      id: 1,
      name: 'Future Shop',
      slug: 'future-shop',
      logo_url: null,
      average_rating: '4.8',
    },
    media: [],
    variants: [],
    attributes: [],
    min_price: '1000000',
    max_price: '1000000',
    rating_average: '4.8',
    rating_count: 10,
    sold_count: 20,
    created_at: '2026-07-01T00:00:00Z',
    updated_at: '2026-07-01T00:00:00Z',
  }
}

function detailResponse(data: PublicProductDetail) {
  return {
    data: {
      success: true,
      message: 'Lấy sản phẩm thành công',
      data,
    },
  } as Awaited<ReturnType<typeof productApi.detail>>
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((promiseResolve) => {
    resolve = promiseResolve
  })
  return { promise, resolve }
}

describe('product store detail loading', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
  })

  it('ignores a stale response after the route changes to another product', async () => {
    const first = deferred<Awaited<ReturnType<typeof productApi.detail>>>()
    const second = deferred<Awaited<ReturnType<typeof productApi.detail>>>()
    vi.mocked(productApi.detail)
      .mockImplementationOnce(() => first.promise)
      .mockImplementationOnce(() => second.promise)
    const store = useProductStore()

    const firstRequest = store.loadDetail('old-product')
    const secondRequest = store.loadDetail('new-product')
    second.resolve(detailResponse(detail('new-product', 'Sản phẩm mới')))
    await secondRequest
    first.resolve(detailResponse(detail('old-product', 'Sản phẩm cũ')))
    await firstRequest

    expect(store.detail?.id).toBe('new-product')
    expect(store.loading).toBe(false)
  })
})
