import { createPinia, type Pinia } from 'pinia'
import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { nextTick } from 'vue'
import { beforeEach, vi } from 'vitest'

import type { AuthenticatedUser } from '@/features/auth/types'
import { productApi } from '@/features/product/api'
import { recordBrowsingProduct } from '@/features/product/browsingHistory'
import type { ProductRecommendationData, PublicProductListItem } from '@/features/product/types'
import { useAuthStore } from '@/stores/auth'

import { homeApi } from '../api'
import type { HomePageData } from '../types'
import HomePageContent from './HomePageContent.vue'

vi.mock('../api', () => ({
  homeApi: {
    get: vi.fn(),
  },
}))

vi.mock('@/features/product/api', () => ({
  productApi: {
    homeRecommendations: vi.fn(),
  },
}))

const product: PublicProductListItem = {
  id: '00000000-0000-4000-8000-000000000001',
  name: 'Điện thoại mới',
  slug: 'dien-thoai-moi',
  thumbnail: null,
  min_price: '4990000',
  max_price: '4990000',
  rating_average: '4.8',
  rating_count: 12,
  sold_count: 8,
  shop_name: 'Future Shop',
  shop_slug: 'future-shop',
}

const customer: AuthenticatedUser = {
  id: 101,
  email: 'customer@example.com',
  role: 'customer',
  is_active: true,
  is_email_verified: true,
  must_change_password: false,
  avatar_url: '',
  full_name: 'Khách hàng',
  phone: '',
  date_of_birth: null,
  gender: '',
  profile: null,
  created_at: '2026-07-29T00:00:00Z',
  updated_at: '2026-07-29T00:00:00Z',
}

const homeData: HomePageData = {
  banners: [
    {
      id: 'banner-1',
      title: 'Ưu đãi hôm nay',
      image_url: 'https://inhongdang.vn/Upload/root/uu-dai-giam-gia-thang-3-2026.jpg',
      target_url: '/products',
      position: 'hero',
      sort_order: 0,
    },
  ],
  new_arrivals: [product],
  best_sellers: [],
  categories: [
    {
      id: 'category-1',
      name: 'Điện thoại',
      slug: 'dien-thoai',
      image_url: null,
    },
  ],
}

const ProductGridStub = {
  props: ['title', 'products', 'emptyMessage'],
  template: `
    <section>
      <h2>{{ title }}</h2>
      <span v-for="item in products" :key="item.id">{{ item.name }}</span>
      <p v-if="!products.length">{{ emptyMessage }}</p>
    </section>
  `,
}

const RecommendationStub = {
  props: ['title', 'products', 'loading'],
  template: `
    <section v-if="loading || products.length">
      <h2>{{ title }}</h2>
      <span v-for="item in products" :key="item.id">{{ item.name }}</span>
    </section>
  `,
}

function homeResponse() {
  return {
    data: {
      success: true,
      message: 'Lấy trang chủ thành công',
      data: homeData,
    },
  } as Awaited<ReturnType<typeof homeApi.get>>
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
  } as Awaited<ReturnType<typeof productApi.homeRecommendations>>
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((promiseResolve) => {
    resolve = promiseResolve
  })
  return { promise, resolve }
}

function mountHome(pinia: Pinia = createPinia()) {
  return mount(HomePageContent, {
    global: {
      plugins: [pinia],
      stubs: {
        RouterLink: RouterLinkStub,
        ProductGrid: ProductGridStub,
        ProductRecommendationCarousel: RecommendationStub,
      },
    },
  })
}

function authenticatedPinia(user: AuthenticatedUser = customer) {
  const pinia = createPinia()
  const authStore = useAuthStore(pinia)
  authStore.user = user
  authStore.accessToken = 'access-token'
  authStore.initialized = true
  return { authStore, pinia }
}

describe('HomePageContent', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.localStorage.clear()
    vi.mocked(homeApi.get).mockResolvedValue(homeResponse())
    vi.mocked(productApi.homeRecommendations).mockResolvedValue(recommendationResponse([]))
  })

  it('renders the home API and does not request recommendations for a guest', async () => {
    const wrapper = mountHome()
    await flushPromises()

    expect(homeApi.get).toHaveBeenCalledOnce()
    expect(productApi.homeRecommendations).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Ưu đãi hôm nay')
    expect(wrapper.text()).toContain('Điện thoại')
    expect(wrapper.text()).toContain('Điện thoại mới')
    expect(wrapper.text()).toContain('Danh sách bán chạy đang được cập nhật.')
    wrapper.unmount()
  })

  it('shows an error and retries the home request', async () => {
    vi.mocked(homeApi.get).mockRejectedValueOnce(new Error('Mất kết nối'))

    const wrapper = mountHome()
    await flushPromises()

    expect(wrapper.text()).toContain('Mất kết nối')
    await wrapper.get('button').trigger('click')
    await flushPromises()

    expect(homeApi.get).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('Ưu đãi hôm nay')
    wrapper.unmount()
  })

  it('requests and renders authenticated home recommendations with user history', async () => {
    const historyId = '00000000-0000-4000-8000-000000000099'
    const recommended = {
      ...product,
      id: '00000000-0000-4000-8000-000000000010',
      name: 'Gợi ý riêng cho bạn',
    }
    const { pinia } = authenticatedPinia()
    recordBrowsingProduct(historyId, customer.id)
    vi.mocked(productApi.homeRecommendations).mockResolvedValue(
      recommendationResponse([recommended]),
    )

    const wrapper = mountHome(pinia)
    await flushPromises()

    expect(productApi.homeRecommendations).toHaveBeenCalledWith([historyId])
    expect(wrapper.text()).toContain('Gợi ý cho bạn')
    expect(wrapper.text()).toContain('Gợi ý riêng cho bạn')
    wrapper.unmount()
  })

  it('keeps the home page usable when recommendations fail', async () => {
    const { pinia } = authenticatedPinia()
    vi.mocked(productApi.homeRecommendations).mockRejectedValue(
      new Error('Recommendation unavailable'),
    )

    const wrapper = mountHome(pinia)
    await flushPromises()

    expect(wrapper.text()).toContain('Ưu đãi hôm nay')
    expect(wrapper.text()).toContain('Điện thoại mới')
    expect(wrapper.text()).not.toContain('Recommendation unavailable')
    wrapper.unmount()
  })

  it('waits for auth hydration and ignores recommendations from a previous user', async () => {
    const firstRequest = deferred<Awaited<ReturnType<typeof productApi.homeRecommendations>>>()
    const secondUser = { ...customer, id: 202, email: 'second@example.com' }
    const firstProduct = {
      ...product,
      id: '00000000-0000-4000-8000-000000000021',
      name: 'Gợi ý người dùng cũ',
    }
    const secondProduct = {
      ...product,
      id: '00000000-0000-4000-8000-000000000022',
      name: 'Gợi ý người dùng mới',
    }
    vi.mocked(productApi.homeRecommendations)
      .mockImplementationOnce(() => firstRequest.promise)
      .mockResolvedValueOnce(recommendationResponse([secondProduct]))

    const pinia = createPinia()
    const authStore = useAuthStore(pinia)
    const wrapper = mountHome(pinia)
    await flushPromises()
    expect(productApi.homeRecommendations).not.toHaveBeenCalled()

    authStore.user = customer
    authStore.accessToken = 'first-token'
    authStore.initialized = true
    await nextTick()
    expect(productApi.homeRecommendations).toHaveBeenCalledTimes(1)

    authStore.user = secondUser
    await flushPromises()
    expect(productApi.homeRecommendations).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('Gợi ý người dùng mới')

    firstRequest.resolve(recommendationResponse([firstProduct]))
    await flushPromises()
    expect(wrapper.text()).not.toContain('Gợi ý người dùng cũ')
    wrapper.unmount()
  })
})
