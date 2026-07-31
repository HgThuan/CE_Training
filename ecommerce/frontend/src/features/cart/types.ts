export interface CartItem {
  id: string
  variant_id: string
  variant_sku: string
  variant_name: string | null
  product_id: string
  product_name: string
  product_slug: string
  primary_image: string | null
  quantity: number
  is_selected: boolean
  unit_price_snapshot: string
  current_price: string
  line_total: string
  available_stock: number
  price_changed: boolean
  is_valid: boolean
}

export interface CartShopGroup {
  shop_id: number
  shop_name: string
  shop_slug: string
  logo_url: string
  items: CartItem[]
  subtotal: string
}

export interface CartData {
  id: string
  total_items: number
  total_selected_items: number
  shops: CartShopGroup[]
  subtotal: string
  updated_at: string
}

export interface GuestCartItem {
  variant_id: string
  quantity: number
  added_at: string
  product_slug?: string
  shop_slug?: string
  cached_product_name?: string
  cached_variant_name?: string | null
  cached_image?: string | null
  cached_price?: string
}

export interface GuestItemContext {
  product_slug: string
  shop_slug?: string
  product_name: string
  variant_name?: string | null
  image?: string | null
  price: string
}

export interface PreviewDiscount {
  scope: 'platform' | 'shop'
  code: string
  amount: string
}

export interface PreviewItem {
  item_id: string
  variant_id: string
  quantity: number
  unit_price: string
  is_flash_sale: boolean
  line_total: string
  category_id: string
}

export interface PreviewShop {
  shop_id: number
  shop_name: string
  items: PreviewItem[]
  subtotal: string
  discounts: PreviewDiscount[]
  total: string
}

export interface PreviewResult {
  shops: PreviewShop[]
  subtotal: string
  discount: string
  total: string
}

export interface CartPreviewPayload {
  selected_item_ids?: string[]
  voucher_codes: {
    platform?: string[]
    shops?: Record<string, string[]>
  }
}
