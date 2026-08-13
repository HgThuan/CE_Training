import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { productApi } from '@/features/product/api'
import { useAuthStore } from '@/stores/auth'

import { cartApi } from './api'
import { GUEST_CART_STORAGE_KEY } from './composables/useGuestCart'
import { useCartStore } from './store'

vi.mock('./api', () => ({
  cartApi: {
    getCart: vi.fn(),
    addItem: vi.fn(),
    updateItem: vi.fn(),
    removeItem: vi.fn(),
    mergeGuestCart: vi.fn(),
    previewCheckout: vi.fn(),
  },
}))

vi.mock('@/features/product/api', () => ({ productApi: { detail: vi.fn() } }))

const emptyCart = {
  id: 'cart-1',
  total_items: 0,
  total_selected_items: 0,
  shops: [],
  subtotal: '0',
  updated_at: '2026-07-31T00:00:00Z',
}

function customerSession(): void {
  const auth = useAuthStore()
  auth.accessToken = 'token'
  auth.user = {
    id: 1,
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
}

describe('cart store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('accumulates duplicate guest variants through addItem', async () => {
    vi.mocked(productApi.detail).mockResolvedValue({
      data: {
        success: true,
        message: 'ok',
        data: {
          id: 'product-1',
          name: 'Product',
          slug: 'product',
          shop: { id: 1, name: 'Shop', slug: 'shop', logo_url: null, average_rating: '0' },
          media: [],
          variants: [
            {
              id: 'variant-1',
              sku: 'SKU',
              name: 'Default',
              original_price: '120000',
              sale_price: '100000',
              stock_quantity: 10,
              available_stock: 10,
              weight_grams: null,
              attributes: [],
            },
          ],
        },
      },
    } as never)
    const store = useCartStore()
    const context = { product_slug: 'product', product_name: 'Product', price: '100000' }
    await store.addItem('variant-1', 1, context)
    await store.addItem('variant-1', 2, context)

    expect(JSON.parse(localStorage.getItem(GUEST_CART_STORAGE_KEY) ?? '[]')[0].quantity).toBe(3)
  })

  it('keeps a minimal guest item visible when product context is unavailable', async () => {
    localStorage.setItem(
      GUEST_CART_STORAGE_KEY,
      JSON.stringify([
        { variant_id: 'variant-1', quantity: 2, added_at: new Date().toISOString() },
      ]),
    )

    const store = useCartStore()
    await store.load()

    expect(store.cart?.total_items).toBe(2)
    expect(store.cart?.shops[0]?.items[0]).toMatchObject({
      variant_id: 'variant-1',
      quantity: 2,
      is_valid: false,
      is_selected: false,
    })
    expect(productApi.detail).not.toHaveBeenCalled()
  })

  it('clears localStorage only after merge succeeds', async () => {
    customerSession()
    localStorage.setItem(
      GUEST_CART_STORAGE_KEY,
      JSON.stringify([
        { variant_id: 'variant-1', quantity: 2, added_at: new Date().toISOString() },
      ]),
    )
    vi.mocked(cartApi.mergeGuestCart).mockResolvedValue({
      data: { success: true, message: 'ok', data: emptyCart },
    } as never)

    expect(await useCartStore().mergeGuestCart()).toBe(true)
    expect(localStorage.getItem(GUEST_CART_STORAGE_KEY)).toBeNull()
  })

  it('keeps localStorage when merge fails', async () => {
    customerSession()
    localStorage.setItem(
      GUEST_CART_STORAGE_KEY,
      JSON.stringify([
        { variant_id: 'variant-1', quantity: 2, added_at: new Date().toISOString() },
      ]),
    )
    vi.mocked(cartApi.mergeGuestCart).mockRejectedValue(new Error('network'))

    expect(await useCartStore().mergeGuestCart()).toBe(false)
    expect(localStorage.getItem(GUEST_CART_STORAGE_KEY)).not.toBeNull()
  })
})
