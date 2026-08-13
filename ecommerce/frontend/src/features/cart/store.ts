import { AxiosError } from 'axios'
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { productApi } from '@/features/product/api'
import type { PublicProductDetail } from '@/features/product/types'
import { promotionApi } from '@/features/promotion/api'
import type { CheckoutVoucher } from '@/features/promotion/types'
import { useAuthStore } from '@/stores/auth'

import { cartApi } from './api'
import { clearGuestCart, readGuestCart, useGuestCart } from './composables/useGuestCart'
import type {
  CartData,
  CartItem,
  CartPreviewPayload,
  CartShopGroup,
  GuestCartItem,
  GuestItemContext,
  PreviewResult,
} from './types'

function errorMessage(error: unknown): string {
  if (!(error instanceof AxiosError)) return 'Đã có lỗi không mong muốn'
  const payload = error.response?.data as
    { message?: string; errors?: Record<string, string[] | string> } | undefined
  if (payload?.message) return payload.message
  return error.response ? 'Không thể xử lý yêu cầu' : 'Không thể kết nối máy chủ'
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
    is_valid: variant.available_stock >= guestQuantity && variant.available_stock > 0,
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
  const cart = ref<CartData | null>(null)
  const preview = ref<PreviewResult | null>(null)
  const loading = ref(false)
  const previewing = ref(false)
  const error = ref('')
  const previewError = ref('')
  const mergeWarning = ref('')
  const platformVoucher = ref('')
  const shopVouchers = ref<Record<string, string>>({})
  const availableVouchers = ref<CheckoutVoucher[]>([])
  const selectedUserVoucherIds = ref<string[]>([])
  const checkoutToken = ref<string>()

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
        await loadAvailableVouchers()
      } else {
        await loadGuestCart()
      }
    } catch (caught) {
      error.value = errorMessage(caught)
    } finally {
      loading.value = false
    }
  }

  async function addItem(
    variantId: string,
    quantity = 1,
    context?: GuestItemContext,
  ): Promise<void> {
    error.value = ''
    if (!isAuthenticatedCustomer.value) {
      guestCart.add(variantId, quantity, context)
      await loadGuestCart()
      return
    }
    try {
      cart.value = (await cartApi.addItem(variantId, quantity)).data.data
    } catch (caught) {
      error.value = errorMessage(caught)
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
      await applyOwnedVouchers()
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
    await applyOwnedVouchers()
  }

  function previewPayload(): CartPreviewPayload {
    const shops = Object.fromEntries(
      Object.entries(shopVouchers.value)
        .filter(([, code]) => code.trim())
        .map(([shopId, code]) => [shopId, [code.trim()]]),
    )
    return {
      selected_item_ids: selectedValidItems.value.map((item) => item.id),
      voucher_codes: {
        platform: platformVoucher.value.trim() ? [platformVoucher.value.trim()] : [],
        shops,
      },
    }
  }

  async function calculatePreview(): Promise<void> {
    previewError.value = ''
    if (!isAuthenticatedCustomer.value) {
      preview.value = null
      previewError.value = 'Đăng nhập để áp voucher và xem giá từ máy chủ'
      return
    }
    previewing.value = true
    try {
      preview.value = (await cartApi.previewCheckout(previewPayload())).data.data
    } catch (caught) {
      preview.value = null
      previewError.value = errorMessage(caught)
    } finally {
      previewing.value = false
    }
  }

  async function loadAvailableVouchers(): Promise<void> {
    if (!isAuthenticatedCustomer.value) return
    previewError.value = ''
    try {
      const data = (
        await promotionApi.checkoutVouchers(selectedValidItems.value.map((item) => item.id))
      ).data.data
      availableVouchers.value = data.results
      selectedUserVoucherIds.value = data.best_voucher_id ? [data.best_voucher_id] : []
      if (selectedUserVoucherIds.value.length) await applyOwnedVouchers()
    } catch (caught) {
      previewError.value = errorMessage(caught)
    }
  }

  async function applyOwnedVouchers(): Promise<void> {
    previewing.value = true
    previewError.value = ''
    try {
      const response = await promotionApi.applyOwnedVouchers({
        user_voucher_ids: selectedUserVoucherIds.value,
        selected_item_ids: selectedValidItems.value.map((item) => item.id),
        checkout_token: checkoutToken.value,
      })
      preview.value = response.data.data
      checkoutToken.value = response.data.data.checkout_token
    } catch (caught) {
      previewError.value = errorMessage(caught)
      throw caught
    } finally {
      previewing.value = false
    }
  }

  async function toggleOwnedVoucher(id: string, selected: boolean): Promise<void> {
    const previous = [...selectedUserVoucherIds.value]
    selectedUserVoucherIds.value = selected
      ? [...selectedUserVoucherIds.value, id]
      : selectedUserVoucherIds.value.filter((value) => value !== id)
    try {
      await applyOwnedVouchers()
    } catch {
      selectedUserVoucherIds.value = previous
    }
  }

  async function applyVoucherByCode(code: string): Promise<void> {
    previewing.value = true
    previewError.value = ''
    try {
      const response = await promotionApi.applyVoucherByCode({
        code,
        idempotency_key: crypto.randomUUID(),
        selected_item_ids: selectedValidItems.value.map((item) => item.id),
        checkout_token: checkoutToken.value,
      })
      preview.value = response.data.data
      checkoutToken.value = response.data.data.checkout_token
      await loadAvailableVouchers()
    } catch (caught) {
      previewError.value = errorMessage(caught)
    } finally {
      previewing.value = false
    }
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
    preview,
    loading,
    previewing,
    error,
    previewError,
    mergeWarning,
    platformVoucher,
    shopVouchers,
    availableVouchers,
    selectedUserVoucherIds,
    isAuthenticatedCustomer,
    selectedValidItems,
    selectedTotal,
    load,
    addItem,
    updateItem,
    removeItem,
    calculatePreview,
    loadAvailableVouchers,
    toggleOwnedVoucher,
    applyOwnedVouchers,
    applyVoucherByCode,
    mergeGuestCart,
  }
})
