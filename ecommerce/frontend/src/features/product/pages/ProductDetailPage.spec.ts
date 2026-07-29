import { createPinia } from 'pinia'
import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, vi } from 'vitest'

import { readBrowsingHistory, recordBrowsingProduct } from '../browsingHistory'
import { productApi } from '../api'
import type {
  ProductRecommendationData,
  PublicProductDetail,
  PublicProductListItem,
} from '../types'
import ProductDetailPage from './ProductDetailPage.vue'

vi.mock('../api', () => ({
  productApi: {
    detail: vi.fn(),
    similar: vi.fn(),
    recommendations: vi.fn(),
  },
}))

const PRODUCT_ONE_ID = '00000000-0000-4000-8000-000000000001'
const PRODUCT_TWO_ID = '00000000-0000-4000-8000-000000000002'
const HISTORY_ID = '00000000-0000-4000-8000-000000000099'

function makeDetail(id: string, name: string, slug: string): PublicProductDetail {
  return {
    id,
    name,
    slug,
    short_description: 'Mô tả ngắn',
    description: 'Mô tả',
    category: {
      id: 'category-1',
      name: 'Điện thoại',
      slug: 'dien-thoai',
    },
    brand: null,
    shop: {
      id: 1,
      name: 'Future Shop',
      slug: 'future-shop',
      logo_url: null,
      average_rating: '4.9',
    },
    media: [],
    variants: [
      {
        id: `${id}-variant`,
        sku: `${slug}-sku`,
        name: null,
        original_price: '4990000',
        sale_price: '4990000',
        stock_quantity: 5,
        available_stock: 5,
        weight_grams: null,
        attributes: [],
      },
    ],
    attributes: [],
    min_price: '4990000',
    max_price: '4990000',
    rating_average: '4.8',
    rating_count: 12,
    sold_count: 8,
    created_at: '2026-07-29T00:00:00Z',
    updated_at: '2026-07-29T00:00:00Z',
  }
}

function makeListItem(id: string, name: string): PublicProductListItem {
  return {
    id,
    name,
    slug: name.toLowerCase().replaceAll(' ', '-'),
    thumbnail: null,
    min_price: '3990000',
    max_price: '3990000',
    rating_average: '4.7',
    rating_count: 10,
    sold_count: 6,
    shop_name: 'Future Shop',
    shop_slug: 'future-shop',
  }
}

function detailResponse(detail: PublicProductDetail) {
  return {
    data: {
      success: true,
      message: 'ok',
      data: detail,
    },
  } as Awaited<ReturnType<typeof productApi.detail>>
}

function recommendationResponse(results: PublicProductListItem[]) {
  const data: ProductRecommendationData = {
    results,
    ai_used: true,
    fallback_used: false,
    personalized: true,
    strategy: 'embedding',
  }
  return {
    data: {
      success: true,
      message: 'ok',
      data,
    },
  } as Awaited<ReturnType<typeof productApi.similar>>
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((promiseResolve) => {
    resolve = promiseResolve
  })
  return { promise, resolve }
}

const RecommendationStub = {
  props: {
    title: { type: String, required: true },
    products: { type: Array, required: true },
    loading: { type: Boolean, default: false },
  },
  template: `
    <section v-if="loading || products.length" class="recommendation-stub">
      <h2>{{ title }}</h2>
      <span v-for="product in products" :key="product.id">{{ product.name }}</span>
    </section>
  `,
}

async function mountPage(url = '/products/product-one') {
  const component = { template: '<div />' }
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component },
      { path: '/products', name: 'product-list', component },
      { path: '/products/:slug', name: 'product-detail', component },
      { path: '/shops/:slug', name: 'public-shop', component },
    ],
  })
  await router.push(url)
  await router.isReady()

  const wrapper = mount(ProductDetailPage, {
    global: {
      plugins: [createPinia(), router],
      stubs: {
        RouterLink: RouterLinkStub,
        ProductGallery: true,
        ProductDetailTabs: true,
        VariantSelector: true,
        WaitlistButton: true,
        WishlistToggleButton: true,
        ProductRecommendationCarousel: RecommendationStub,
      },
    },
  })

  return { router, wrapper }
}

describe('ProductDetailPage recommendations', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.localStorage.clear()
  })

  it('loads both sections with the history snapshot before recording the current product', async () => {
    const detail = makeDetail(PRODUCT_ONE_ID, 'Sản phẩm một', 'product-one')
    const similar = makeListItem('00000000-0000-4000-8000-000000000011', 'Sản phẩm tương tự một')
    const recommended = makeListItem('00000000-0000-4000-8000-000000000012', 'Sản phẩm đề xuất một')
    vi.mocked(productApi.detail).mockResolvedValue(detailResponse(detail))
    vi.mocked(productApi.similar).mockResolvedValue(recommendationResponse([similar]))
    vi.mocked(productApi.recommendations).mockResolvedValue(recommendationResponse([recommended]))
    recordBrowsingProduct(HISTORY_ID)

    const { wrapper } = await mountPage()
    await flushPromises()

    expect(productApi.similar).toHaveBeenCalledWith(PRODUCT_ONE_ID)
    expect(productApi.recommendations).toHaveBeenCalledWith(PRODUCT_ONE_ID, [HISTORY_ID])
    expect(readBrowsingHistory()).toEqual([PRODUCT_ONE_ID, HISTORY_ID])
    expect(wrapper.text()).toContain('Sản phẩm tương tự một')
    expect(wrapper.text()).toContain('Sản phẩm đề xuất một')
    wrapper.unmount()
  })

  it('keeps recommendations and product content when the similar request fails', async () => {
    const detail = makeDetail(PRODUCT_ONE_ID, 'Sản phẩm một', 'product-one')
    const recommended = makeListItem('00000000-0000-4000-8000-000000000012', 'Đề xuất vẫn hiển thị')
    vi.mocked(productApi.detail).mockResolvedValue(detailResponse(detail))
    vi.mocked(productApi.similar).mockRejectedValue(new Error('Similar unavailable'))
    vi.mocked(productApi.recommendations).mockResolvedValue(recommendationResponse([recommended]))

    const { wrapper } = await mountPage()
    await flushPromises()

    expect(wrapper.text()).toContain('Sản phẩm một')
    expect(wrapper.text()).toContain('Đề xuất vẫn hiển thị')
    expect(wrapper.text()).not.toContain('Similar unavailable')
    expect(wrapper.text()).not.toContain('Sản phẩm tương tự')
    wrapper.unmount()
  })

  it('does not render stale suggestions after navigating to another product', async () => {
    const firstDetail = makeDetail(PRODUCT_ONE_ID, 'Sản phẩm một', 'product-one')
    const secondDetail = makeDetail(PRODUCT_TWO_ID, 'Sản phẩm hai', 'product-two')
    const oldSimilarRequest = deferred<Awaited<ReturnType<typeof productApi.similar>>>()
    const oldRecommendationRequest =
      deferred<Awaited<ReturnType<typeof productApi.recommendations>>>()
    const nextSimilar = makeListItem(
      '00000000-0000-4000-8000-000000000021',
      'Tương tự sản phẩm hai',
    )
    const nextRecommendation = makeListItem(
      '00000000-0000-4000-8000-000000000022',
      'Đề xuất sản phẩm hai',
    )

    vi.mocked(productApi.detail).mockImplementation((slug) =>
      Promise.resolve(detailResponse(slug === 'product-one' ? firstDetail : secondDetail)),
    )
    vi.mocked(productApi.similar).mockImplementation((productId) =>
      productId === PRODUCT_ONE_ID
        ? oldSimilarRequest.promise
        : Promise.resolve(recommendationResponse([nextSimilar])),
    )
    vi.mocked(productApi.recommendations).mockImplementation((productId) =>
      productId === PRODUCT_ONE_ID
        ? oldRecommendationRequest.promise
        : Promise.resolve(recommendationResponse([nextRecommendation])),
    )

    const { router, wrapper } = await mountPage()
    await flushPromises()
    await router.push('/products/product-two')
    await flushPromises()

    oldSimilarRequest.resolve(
      recommendationResponse([
        makeListItem('00000000-0000-4000-8000-000000000031', 'Kết quả cũ tương tự'),
      ]),
    )
    oldRecommendationRequest.resolve(
      recommendationResponse([
        makeListItem('00000000-0000-4000-8000-000000000032', 'Kết quả cũ đề xuất'),
      ]),
    )
    await flushPromises()

    expect(wrapper.text()).toContain('Sản phẩm hai')
    expect(wrapper.text()).toContain('Tương tự sản phẩm hai')
    expect(wrapper.text()).toContain('Đề xuất sản phẩm hai')
    expect(wrapper.text()).not.toContain('Kết quả cũ')
    wrapper.unmount()
  })
})
