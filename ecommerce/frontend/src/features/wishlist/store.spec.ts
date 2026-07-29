import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'
import { beforeEach, vi } from 'vitest'

import type { AuthenticatedUser } from '@/features/auth/types'
import type { PublicProductListItem } from '@/features/product/types'
import { useAuthStore } from '@/stores/auth'

import { wishlistApi } from './api'
import { useWishlistStore } from './store'
import type { WishlistItem } from './types'

vi.mock('./api', () => ({
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

function product(id: string): PublicProductListItem {
  return {
    id,
    name: `Sản phẩm ${id}`,
    slug: id,
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

function item(id: string): WishlistItem {
  return {
    id: `item-${id}`,
    product: product(id),
    price_when_added: '100000',
    created_at: '2026-07-01T00:00:00Z',
  }
}

function listResponse(
  data: WishlistItem[],
  page = 1,
  totalPages = 1,
  totalItems = data.length,
): Awaited<ReturnType<typeof wishlistApi.list>> {
  return {
    data: {
      success: true,
      message: 'ok',
      data,
      meta: {
        page,
        page_size: 100,
        total_items: totalItems,
        total_pages: totalPages,
      },
    },
  } as Awaited<ReturnType<typeof wishlistApi.list>>
}

function setupStore() {
  setActivePinia(createPinia())
  const authStore = useAuthStore()
  authStore.user = customer
  authStore.accessToken = 'token'
  return { authStore, store: useWishlistStore() }
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((promiseResolve) => {
    resolve = promiseResolve
  })
  return { promise, resolve }
}

describe('wishlist store', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('hydrates membership across every wishlist page', async () => {
    vi.mocked(wishlistApi.list)
      .mockResolvedValueOnce(listResponse([item('product-1')], 1, 2, 2))
      .mockResolvedValueOnce(listResponse([item('product-2')], 2, 2, 2))
    const { store } = setupStore()

    await store.hydrateMembership()

    expect(wishlistApi.list).toHaveBeenCalledTimes(2)
    expect(store.isWishlisted('product-1')).toBe(true)
    expect(store.isWishlisted('product-2')).toBe(true)
  })

  it('updates the loaded page after removing an item', async () => {
    vi.mocked(wishlistApi.list).mockResolvedValue(listResponse([item('product-1')]))
    vi.mocked(wishlistApi.toggle).mockResolvedValue({
      data: {
        success: true,
        message: 'removed',
        data: {
          product_id: 'product-1',
          is_wishlisted: false,
          item: null,
        },
      },
    } as Awaited<ReturnType<typeof wishlistApi.toggle>>)
    const { store } = setupStore()
    await store.loadPage()

    await store.toggle('product-1')

    expect(store.items).toHaveLength(0)
    expect(store.meta.total_items).toBe(0)
    expect(store.isWishlisted('product-1')).toBe(false)
  })

  it('blocks a duplicate toggle while the first request is pending', async () => {
    const request = deferred<Awaited<ReturnType<typeof wishlistApi.toggle>>>()
    vi.mocked(wishlistApi.toggle).mockImplementation(() => request.promise)
    const { store } = setupStore()

    const first = store.toggle('product-1')
    const duplicate = store.toggle('product-1')
    request.resolve({
      data: {
        success: true,
        message: 'added',
        data: {
          product_id: 'product-1',
          is_wishlisted: true,
          item: item('product-1'),
        },
      },
    } as Awaited<ReturnType<typeof wishlistApi.toggle>>)
    await Promise.all([first, duplicate])

    expect(wishlistApi.toggle).toHaveBeenCalledOnce()
    expect(store.isWishlisted('product-1')).toBe(true)
  })

  it('clears private state when the authenticated user changes', async () => {
    vi.mocked(wishlistApi.list).mockResolvedValue(listResponse([item('product-1')]))
    const { authStore, store } = setupStore()
    await store.hydrateMembership()

    authStore.clearSession()
    await nextTick()

    expect(store.isWishlisted('product-1')).toBe(false)
    expect(store.items).toHaveLength(0)
  })
})
