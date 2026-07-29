import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, vi } from 'vitest'

import type { AuthenticatedUser } from '@/features/auth/types'
import { useAuthStore } from '@/stores/auth'

import { wishlistApi } from '../api'
import type { WishlistItem } from '../types'
import WishlistPage from './WishlistPage.vue'

vi.mock('../api', () => ({
  wishlistApi: {
    list: vi.fn(),
    toggle: vi.fn(),
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

const item: WishlistItem = {
  id: 'item-1',
  product: {
    id: 'product-1',
    name: 'Điện thoại yêu thích',
    slug: 'dien-thoai',
    thumbnail: null,
    min_price: '100000',
    max_price: '100000',
    rating_average: '4.8',
    rating_count: 10,
    sold_count: 20,
    shop_name: 'Future Shop',
    shop_slug: 'future-shop',
  },
  price_when_added: '120000',
  created_at: '2026-07-01T00:00:00Z',
}

function response(data: WishlistItem[]) {
  return {
    data: {
      success: true,
      message: 'ok',
      data,
      meta: {
        page: 1,
        page_size: 12,
        total_items: data.length,
        total_pages: data.length ? 1 : 0,
      },
    },
  } as Awaited<ReturnType<typeof wishlistApi.list>>
}

async function mountPage() {
  const component = { template: '<div />' }
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/wishlist', name: 'wishlist', component },
      { path: '/products', component },
    ],
  })
  await router.push('/wishlist')
  await router.isReady()
  const pinia = createPinia()
  const authStore = useAuthStore(pinia)
  authStore.user = customer
  authStore.accessToken = 'token'
  const wrapper = mount(WishlistPage, {
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
  return wrapper
}

describe('WishlistPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders an empty state with a catalog call to action', async () => {
    vi.mocked(wishlistApi.list).mockResolvedValue(response([]))
    const wrapper = await mountPage()

    expect(wrapper.text()).toContain('Wishlist đang trống')
    expect(wrapper.get('a').attributes('href')).toBe('/products')
    wrapper.unmount()
  })

  it('shows an error, retries and renders wishlist products', async () => {
    vi.mocked(wishlistApi.list)
      .mockRejectedValueOnce(new Error('Mất kết nối'))
      .mockResolvedValueOnce(response([item]))
    const wrapper = await mountPage()
    expect(wrapper.text()).toContain('Mất kết nối')

    await wrapper.get('button').trigger('click')
    await flushPromises()

    expect(wishlistApi.list).toHaveBeenCalledTimes(2)
    expect(wrapper.get('[data-test="product-card"]').text()).toBe('Điện thoại yêu thích')
    expect(wrapper.text()).toContain('120.000')
    wrapper.unmount()
  })
})
