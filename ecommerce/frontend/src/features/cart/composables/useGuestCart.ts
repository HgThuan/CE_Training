import { ref } from 'vue'

import type { GuestCartItem, GuestItemContext } from '../types'

export const GUEST_CART_STORAGE_KEY = 'mercato_guest_cart_v1'

function isGuestCartItem(value: unknown): value is GuestCartItem {
  if (!value || typeof value !== 'object') return false
  const item = value as Partial<GuestCartItem>
  return (
    typeof item.variant_id === 'string' &&
    item.variant_id.length > 0 &&
    typeof item.quantity === 'number' &&
    Number.isInteger(item.quantity) &&
    item.quantity > 0 &&
    typeof item.added_at === 'string'
  )
}

export function readGuestCart(): GuestCartItem[] {
  try {
    const raw = localStorage.getItem(GUEST_CART_STORAGE_KEY)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.filter(isGuestCartItem)
  } catch {
    return []
  }
}

export function writeGuestCart(items: GuestCartItem[]): void {
  localStorage.setItem(GUEST_CART_STORAGE_KEY, JSON.stringify(items))
}

export function clearGuestCart(): void {
  localStorage.removeItem(GUEST_CART_STORAGE_KEY)
}

export function useGuestCart() {
  const items = ref<GuestCartItem[]>(readGuestCart())

  function persist(): void {
    writeGuestCart(items.value)
  }

  function add(variantId: string, quantity: number, context?: GuestItemContext): void {
    const existing = items.value.find((item) => item.variant_id === variantId)
    if (existing) {
      existing.quantity += quantity
      if (context) {
        existing.product_slug = context.product_slug
        existing.shop_slug = context.shop_slug
        existing.cached_product_name = context.product_name
        existing.cached_variant_name = context.variant_name
        existing.cached_image = context.image
        existing.cached_price = context.price
      }
    } else {
      items.value.push({
        variant_id: variantId,
        quantity,
        added_at: new Date().toISOString(),
        product_slug: context?.product_slug,
        shop_slug: context?.shop_slug,
        cached_product_name: context?.product_name,
        cached_variant_name: context?.variant_name,
        cached_image: context?.image,
        cached_price: context?.price,
      })
    }
    persist()
  }

  function update(variantId: string, quantity: number): void {
    const item = items.value.find((entry) => entry.variant_id === variantId)
    if (!item) return
    item.quantity = Math.max(1, quantity)
    persist()
  }

  function remove(variantId: string): void {
    items.value = items.value.filter((item) => item.variant_id !== variantId)
    persist()
  }

  function clear(): void {
    items.value = []
    clearGuestCart()
  }

  function reload(): void {
    items.value = readGuestCart()
  }

  return { items, add, update, remove, clear, reload }
}
