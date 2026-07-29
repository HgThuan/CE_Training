import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, vi } from 'vitest'

import type { AuthenticatedUser } from '@/features/auth/types'
import { useAuthStore } from '@/stores/auth'

import { wishlistApi } from '../api'
import type { WishlistItem } from '../types'
import WishlistToggleButton from './WishlistToggleButton.vue'

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

const wishlistItem: WishlistItem = {
  id: 'item-1',
  product: {
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
  },
  price_when_added: '100000',
  created_at: '2026-07-01T00:00:00Z',
}

async function mountButton(user: AuthenticatedUser | null = null) {
  const component = { template: '<div />' }
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/products/:slug', component },
      { path: '/auth/login', name: 'login', component },
    ],
  })
  await router.push('/products/dien-thoai?shop=future-shop')
  await router.isReady()
  const pinia = createPinia()
  const authStore = useAuthStore(pinia)
  authStore.user = user
  authStore.accessToken = user ? 'token' : null
  const wrapper = mount(WishlistToggleButton, {
    props: {
      productId: 'product-1',
      productName: 'Điện thoại',
    },
    global: { plugins: [pinia, router] },
  })
  await flushPromises()
  return { router, wrapper }
}

describe('WishlistToggleButton', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(wishlistApi.list).mockResolvedValue({
      data: {
        success: true,
        message: 'ok',
        data: [],
        meta: {
          page: 1,
          page_size: 100,
          total_items: 0,
          total_pages: 0,
        },
      },
    } as unknown as Awaited<ReturnType<typeof wishlistApi.list>>)
    vi.mocked(wishlistApi.toggle).mockResolvedValue({
      data: {
        success: true,
        message: 'added',
        data: {
          product_id: 'product-1',
          is_wishlisted: true,
          item: wishlistItem,
        },
      },
    } as Awaited<ReturnType<typeof wishlistApi.toggle>>)
  })

  it('redirects a guest to login with the current product URL', async () => {
    const { router, wrapper } = await mountButton()

    await wrapper.get('button').trigger('click')
    await flushPromises()

    expect(wishlistApi.toggle).not.toHaveBeenCalled()
    expect(router.currentRoute.value.name).toBe('login')
    expect(router.currentRoute.value.query.redirect).toBe('/products/dien-thoai?shop=future-shop')
    wrapper.unmount()
  })

  it('toggles wishlist for a customer and updates accessible state', async () => {
    const { wrapper } = await mountButton(customer)
    expect(wrapper.get('button').attributes('aria-pressed')).toBe('false')

    await wrapper.get('button').trigger('click')
    await flushPromises()

    expect(wishlistApi.toggle).toHaveBeenCalledWith('product-1')
    expect(wrapper.get('button').attributes('aria-pressed')).toBe('true')
    expect(wrapper.get('button').attributes('aria-label')).toContain('Bỏ')
    wrapper.unmount()
  })

  it('does not call the customer endpoint for a seller', async () => {
    const seller = { ...customer, id: 20, role: 'seller' as const }
    const { wrapper } = await mountButton(seller)

    expect(wrapper.get('button').attributes('disabled')).toBeDefined()
    expect(wishlistApi.list).not.toHaveBeenCalled()
    expect(wishlistApi.toggle).not.toHaveBeenCalled()
    wrapper.unmount()
  })
})
