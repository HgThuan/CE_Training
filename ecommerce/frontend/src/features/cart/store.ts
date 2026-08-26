import { AxiosError } from 'axios'
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { productApi } from '@/features/product/api'
import type { ProductVariant, PublicProductDetail } from '@/features/product/types'
import { useAuthStore } from '@/stores/auth'

import { cartApi } from './api'
import { useCartToast } from './composables/useCartToast'
import { clearGuestCart, readGuestCart, useGuestCart } from './composables/useGuestCart'
import type { CartData, CartItem, CartShopGroup, GuestCartItem, GuestItemContext } from './types'

function errorMessage(error: unknown): string {
  if (!(error instanceof AxiosError)) return 'Đã có lỗi không mong muốn'
  const payload = error.response?.data as
    { message?: string; errors?: Record<string, string[] | string> } | undefined
  if (payload?.message) return payload.message
  return error.response ? 'Không thể xử lý yêu cầu' : 'Không thể kết nối máy chủ'
}

function purchasableStock(variant: ProductVariant): number {
  const inventoryStock = Math.max(0, variant.available_stock)
  const flashQuota = variant.remaining_flash_quota
  return Math.min(inventoryStock, flashQuota ?? inventoryStock)
}

function guestGroup(
  product: PublicProductDetail,
  guestQuantity: number,
  variantId: string,
): CartItem {
  const variant = product.variants.find((entry) => entry.id === variantId)
  if (!variant) throw new Error('Biến thể không còn tồn tại')
  const image =
    product.media.find((entry) => entry.variant_id === variant.id && entry.is_primary) ??
    product.media.find((entry) => entry.is_primary) ??
    product.media[0]
  const cached = readGuestCart().find((entry) => entry.variant_id === variantId)
  const currentPrice = variant.sale_price
  const snapshot = cached?.cached_price ?? currentPrice
  return {
    id: `guest:${variant.id}`,
    variant_id: variant.id,
    variant_sku: variant.sku,
    variant_name: variant.name,
    product_id: product.id,
    product_name: product.name,
    product_slug: product.slug,
    primary_image: image?.file_url ?? null,
    quantity: guestQuantity,
    is_selected: true,
    unit_price_snapshot: snapshot,
    current_price: currentPrice,
    line_total: String(Number(currentPrice) * guestQuantity),
    available_stock: variant.available_stock,
    price_changed: Number(snapshot) !== Number(currentPrice),
    is_valid: purchasableStock(variant) >= guestQuantity,
  }
}

function unavailableGuestEntry(guest: GuestCartItem): {
  product: PublicProductDetail
  item: CartItem
} {
  const productSlug = guest.product_slug ?? ''
  return {
    product: {
      id: guest.variant_id,
      name: guest.cached_product_name ?? 'Sản phẩm không còn khả dụng',
      slug: productSlug,
      shop: {
        id: -1,
        name: 'Không xác định',
        slug: guest.shop_slug ?? '',
        logo_url: null,
        average_rating: '0',
      },
    } as PublicProductDetail,
    item: {
      id: `guest:${guest.variant_id}`,
      variant_id: guest.variant_id,
      variant_sku: '',
      variant_name: guest.cached_variant_name ?? null,
      product_id: guest.variant_id,
      product_name: guest.cached_product_name ?? 'Sản phẩm không còn khả dụng',
      product_slug: productSlug,
      primary_image: guest.cached_image ?? null,
      quantity: guest.quantity,
      is_selected: false,
      unit_price_snapshot: guest.cached_price ?? '0',
      current_price: guest.cached_price ?? '0',
      line_total: '0',
      available_stock: 0,
      price_changed: false,
      is_valid: false,
    },
  }
}

export const useCartStore = defineStore('cart', () => {
  const authStore = useAuthStore()
  const guestCart = useGuestCart()
  const cartToast = useCartToast()
  const cart = ref<CartData | null>(null)
  const loading = ref(false)
  const error = ref('')
  const mergeWarning = ref('')

  const isAuthenticatedCustomer = computed(
    () => authStore.isAuthenticated && authStore.user?.role === 'customer',
  )
  const selectedValidItems = computed(
    () =>
      cart.value?.shops.flatMap((shop) =>
        shop.items.filter((item) => item.is_selected && item.is_valid),
      ) ?? [],
  )
  const selectedTotal = computed(() =>
    selectedValidItems.value.reduce(
      (total, item) => total + Number(item.current_price) * item.quantity,
      0,
    ),
  )

  async function loadGuestCart(): Promise<void> {
    guestCart.reload()
    if (!guestCart.items.value.length) {
      cart.value = {
        id: 'guest',
        total_items: 0,
        total_selected_items: 0,
        shops: [],
        subtotal: '0',
        updated_at: new Date().toISOString(),
      }
      return
    }
    const rendered: Array<{ product: PublicProductDetail; item: CartItem }> = []
    for (const guest of guestCart.items.value) {
      if (!guest.product_slug) {
        rendered.push(unavailableGuestEntry(guest))
        continue
      }
      try {
        const response = await productApi.detail(guest.product_slug, guest.shop_slug)
        rendered.push({
          product: response.data.data,
          item: guestGroup(response.data.data, guest.quantity, guest.variant_id),
        })
      } catch {
        rendered.push(unavailableGuestEntry(guest))
      }
    }
    const groups = new Map<number, CartShopGroup>()
    for (const entry of rendered) {
      const shop = entry.product.shop
      const group = groups.get(shop.id) ?? {
        shop_id: shop.id,
        shop_name: shop.name,
        shop_slug: shop.slug,
        logo_url: shop.logo_url ?? '',
        items: [],
        subtotal: '0',
      }
      group.items.push(entry.item)
      group.subtotal = String(
        group.items
          .filter((item) => item.is_selected && item.is_valid)
          .reduce((sum, item) => sum + Number(item.current_price) * item.quantity, 0),
      )
      groups.set(shop.id, group)
    }
    const shops = [...groups.values()]
    cart.value = {
      id: 'guest',
      total_items: shops
        .flatMap((shop) => shop.items)
        .reduce((sum, item) => sum + item.quantity, 0),
      total_selected_items: shops
        .flatMap((shop) => shop.items)
        .filter((item) => item.is_selected)
        .reduce((sum, item) => sum + item.quantity, 0),
      shops,
      subtotal: String(shops.reduce((sum, shop) => sum + Number(shop.subtotal), 0)),
      updated_at: new Date().toISOString(),
    }
  }

  async function load(): Promise<void> {
    loading.value = true
    error.value = ''
    try {
      if (isAuthenticatedCustomer.value) {
        cart.value = (await cartApi.getCart()).data.data
      } else {
        await loadGuestCart()
      }
    } catch (caught) {
      error.value = errorMessage(caught)
    } finally {
      loading.value = false
    }
  }

  async function addGuestItem(
    variantId: string,
    quantity: number,
    context?: GuestItemContext,
  ): Promise<void> {
    if (!Number.isInteger(quantity) || quantity <= 0) {
      error.value = 'Số lượng sản phẩm phải lớn hơn 0'
      throw new Error(error.value)
    }
    if (!context?.product_slug) {
      error.value = 'Không thể xác minh tồn kho của sản phẩm này'
      throw new Error(error.value)
    }

    const response = await productApi.detail(context.product_slug, context.shop_slug)
    const variant = response.data.data.variants.find((entry) => entry.id === variantId)
    if (!variant) {
      error.value = 'Biến thể không còn khả dụng'
      throw new Error(error.value)
    }

    const existingQuantity =
      readGuestCart().find((entry) => entry.variant_id === variantId)?.quantity ?? 0
    const targetQuantity = existingQuantity + quantity
    const available = purchasableStock(variant)
    if (available <= 0) {
      error.value = 'Sản phẩm đã hết hàng'
      throw new Error(error.value)
    }
    if (targetQuantity > available) {
      error.value = `Chỉ còn ${available} sản phẩm khả dụng`
      throw new Error(error.value)
    }

    guestCart.add(variantId, quantity, context)
    await loadGuestCart()
  }

  async function addItem(
    variantId: string,
    quantity = 1,
    context?: GuestItemContext,
  ): Promise<void> {
    error.value = ''
    try {
      if (!isAuthenticatedCustomer.value) {
        await addGuestItem(variantId, quantity, context)
      } else {
        cart.value = (await cartApi.addItem(variantId, quantity)).data.data
      }
      cartToast.show({
        status: 'success',
        item: context
          ? {
              product_name: context.product_name,
              variant_name: context.variant_name,
              quantity,
              price: context.price,
              image: context.image,
            }
          : undefined,
      })
    } catch (caught) {
      if (!error.value) error.value = errorMessage(caught)
      cartToast.show({ status: 'error', message: error.value })
      throw caught
    }
  }

  async function updateItem(
    item: CartItem,
    payload: { quantity?: number; is_selected?: boolean },
  ): Promise<void> {
    error.value = ''
    if (!isAuthenticatedCustomer.value) {
      if (payload.quantity) guestCart.update(item.variant_id, payload.quantity)
      await loadGuestCart()
      return
    }
    try {
      cart.value = (await cartApi.updateItem(item.id, payload)).data.data
    } catch (caught) {
      error.value = errorMessage(caught)
      throw caught
    }
  }

  async function removeItem(item: CartItem): Promise<void> {
    if (!isAuthenticatedCustomer.value) {
      guestCart.remove(item.variant_id)
      await loadGuestCart()
      return
    }
    cart.value = (await cartApi.removeItem(item.id)).data.data
  }

  async function mergeGuestCart(): Promise<boolean> {
    const items = readGuestCart()
    if (!items.length || authStore.user?.role !== 'customer') return true
    mergeWarning.value = ''
    try {
      cart.value = (await cartApi.mergeGuestCart(items)).data.data
      clearGuestCart()
      guestCart.reload()
      return true
    } catch (caught) {
      mergeWarning.value = `Đăng nhập thành công nhưng chưa thể gộp giỏ: ${errorMessage(caught)}`
      return false
    }
  }

  return {
    cart,
    loading,
    error,
    mergeWarning,
    isAuthenticatedCustomer,
    selectedValidItems,
    selectedTotal,
    load,
    addItem,
    updateItem,
    removeItem,
    mergeGuestCart,
  }
})
