import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, vi } from 'vitest'

import type { AuthenticatedUser } from '@/features/auth/types'
import type { PublicProductListItem } from '@/features/product/types'
import { useAuthStore } from '@/stores/auth'

import { shopApi } from '../api'
import type { PublicShopData } from '../types'
import PublicShopPage from './PublicShopPage.vue'

vi.mock('../api', () => ({
  shopApi: {
    getPublicShop: vi.fn(),
    toggleFollow: vi.fn(),
  },
}))

const customer: AuthenticatedUser = {
  id: 10,
  email: 'customer@example.com',
  role: 'customer',
  is_active: true,
  is_email_verified: true,
  must_change_password: false,
  avatar_url: '',
  full_name: 'Customer',
  phone: '',
  date_of_birth: null,
  gender: '',
  profile: null,
  created_at: '',
  updated_at: '',
}

const product: PublicProductListItem = {
  id: 'product-1',
  name: 'Điện thoại',
  slug: 'dien-thoai',
  thumbnail: null,
  min_price: '100000',
  max_price: '100000',
  rating_average: '4.8',
  rating_count: 10,
  sold_count: 20,
  shop_name: 'Future Shop',
  shop_slug: 'future-shop',
}

function shopData(slug = 'future-shop', name = 'Future Shop'): PublicShopData {
  return {
    shop: {
      id: slug === 'future-shop' ? 1 : 2,
      name,
      slug,
      description: 'Gian hàng công nghệ',
      logo_url: '',
      cover_url: '',
      average_rating: '4.8',
      total_products: 1,
      follower_count: 3,
      is_following: false,
      created_at: '2026-07-01T00:00:00Z',
    },
    products: [{ ...product, shop_name: name, shop_slug: slug }],
    available_filters: ['category'],
    available_sorts: ['newest', 'price_asc', 'price_desc', 'rating'],
  }
}

function response(data: PublicShopData) {
  return {
    data: {
      success: true,
      message: 'ok',
      data,
      meta: {
        page: 1,
        page_size: 12,
        total_items: data.products.length,
        total_pages: data.products.length ? 1 : 0,
      },
    },
  } as Awaited<ReturnType<typeof shopApi.getPublicShop>>
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((promiseResolve) => {
    resolve = promiseResolve
  })
  return { promise, resolve }
}

async function mountPage(user: AuthenticatedUser | null = null) {
  const component = { template: '<div />' }
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/shops/:slug', name: 'public-shop', component },
      { path: '/auth/login', name: 'login', component },
    ],
  })
  await router.push('/shops/future-shop')
  await router.isReady()
  const pinia = createPinia()
  const authStore = useAuthStore(pinia)
  authStore.user = user
  authStore.accessToken = user ? 'token' : null
  const wrapper = mount(PublicShopPage, {
    global: {
      plugins: [pinia, router],
      stubs: {
        ProductCard: {
          props: ['product'],
          template: '<article data-test="product-card">{{ product.name }}</article>',
        },
      },
    },
  })
  await flushPromises()
  return { router, wrapper }
}

describe('PublicShopPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(shopApi.getPublicShop).mockResolvedValue(response(shopData()))
    vi.mocked(shopApi.toggleFollow).mockResolvedValue({
      data: {
        success: true,
        message: 'followed',
        data: {
          shop_id: 1,
          is_following: true,
          follower_count: 4,
        },
      },
    } as Awaited<ReturnType<typeof shopApi.toggleFollow>>)
  })

  it('renders public products and updates follow state for a customer', async () => {
    const { wrapper } = await mountPage(customer)

    expect(wrapper.get('[data-test="product-card"]').text()).toBe('Điện thoại')
    expect(wrapper.text()).toContain('3 người theo dõi')
    await wrapper.get('button[aria-pressed="false"]').trigger('click')
    await flushPromises()

    expect(shopApi.toggleFollow).toHaveBeenCalledWith(1)
    expect(wrapper.get('button[aria-pressed="true"]').text()).toContain('Đang theo dõi')
    expect(wrapper.text()).toContain('4 người theo dõi')
    wrapper.unmount()
  })

  it('redirects a guest to login without calling the follow endpoint', async () => {
    const { router, wrapper } = await mountPage()

    await wrapper.get('button[aria-pressed="false"]').trigger('click')
    await flushPromises()

    expect(shopApi.toggleFollow).not.toHaveBeenCalled()
    expect(router.currentRoute.value.name).toBe('login')
    expect(router.currentRoute.value.query.redirect).toBe('/shops/future-shop')
    wrapper.unmount()
  })

  it('ignores a stale response after navigating to another shop slug', async () => {
    const first = deferred<Awaited<ReturnType<typeof shopApi.getPublicShop>>>()
    const second = deferred<Awaited<ReturnType<typeof shopApi.getPublicShop>>>()
    vi.mocked(shopApi.getPublicShop)
      .mockImplementationOnce(() => first.promise)
      .mockImplementationOnce(() => second.promise)
    const { router, wrapper } = await mountPage()

    await router.push('/shops/next-shop')
    second.resolve(response(shopData('next-shop', 'Next Shop')))
    await flushPromises()
    first.resolve(response(shopData()))
    await flushPromises()

    expect(wrapper.text()).toContain('Next Shop')
    expect(wrapper.text()).not.toContain('Future Shop')
    wrapper.unmount()
  })

  it('shows an error and retries the shop request', async () => {
    vi.mocked(shopApi.getPublicShop)
      .mockRejectedValueOnce(new Error('Không tải được gian hàng'))
      .mockResolvedValueOnce(response(shopData()))
    const { wrapper } = await mountPage()
    expect(wrapper.text()).toContain('Không tải được gian hàng')

    await wrapper.get('button').trigger('click')
    await flushPromises()

    expect(shopApi.getPublicShop).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('Future Shop')
    wrapper.unmount()
  })
})
