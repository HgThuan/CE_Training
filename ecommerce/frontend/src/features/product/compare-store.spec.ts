import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, vi } from 'vitest'

import { productApi } from './api'
import { MAX_COMPARE_PRODUCTS, useCompareStore } from './compare-store'
import type { PublicProductListItem } from './types'

vi.mock('./api', () => ({
  productApi: { compareProducts: vi.fn() },
}))

function product(index: number): PublicProductListItem {
  return {
    id: `product-${index}`,
    name: `Sản phẩm ${index}`,
    slug: `san-pham-${index}`,
    thumbnail: null,
    min_price: '100000',
    max_price: '100000',
    rating_average: '4.8',
    rating_count: 10,
    sold_count: 20,
    shop_name: 'Future Shop',
    shop_slug: 'future-shop',
  }
}

describe('product comparison store', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
  })

  it('shares selection, supports removal, and enforces the four-product limit', () => {
    const store = useCompareStore()
    for (let index = 1; index <= MAX_COMPARE_PRODUCTS; index += 1) {
      expect(store.toggle(product(index))).toBe(true)
    }

    expect(store.selectedProductIds).toEqual(['product-1', 'product-2', 'product-3', 'product-4'])
    expect(store.isFull).toBe(true)
    expect(store.toggle(product(5))).toBe(false)
    expect(store.selectedProductIds).toHaveLength(4)

    expect(store.toggle(product(2))).toBe(false)
    expect(store.selectedProductIds).toEqual(['product-1', 'product-3', 'product-4'])
    expect(store.isFull).toBe(false)
  })

  it('only enables comparison from two products and sends the shared IDs', async () => {
    const store = useCompareStore()
    store.toggle(product(1))
    expect(store.canCompare).toBe(false)
    expect(await store.compare()).toBe(false)

    store.toggle(product(2))
    vi.mocked(productApi.compareProducts).mockResolvedValue({
      data: {
        success: true,
        message: 'ok',
        data: {
          products: [
            { id: 'product-1', name: 'Sản phẩm 1' },
            { id: 'product-2', name: 'Sản phẩm 2' },
          ],
          rows: [],
          recommendations: [],
          is_comparable: true,
          compatibility_message: null,
          is_ai_generated: false,
          ai_label: null,
        },
      },
    } as unknown as Awaited<ReturnType<typeof productApi.compareProducts>>)

    expect(await store.compare()).toBe(true)
    expect(productApi.compareProducts).toHaveBeenCalledWith(['product-1', 'product-2'])
    expect(store.comparison?.products).toHaveLength(2)
  })
})
