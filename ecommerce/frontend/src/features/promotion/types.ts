export type VoucherScope = 'platform' | 'shop'
export type DiscountType = 'percentage' | 'fixed_amount'

export interface Voucher {
  id: string
  scope: VoucherScope
  shop: number | null
  shop_name: string | null
  code: string
  name: string
  description: string
  discount_type: DiscountType
  discount_value: string
  max_discount_amount: string | null
  min_order_amount: string
  total_usage_limit: number | null
  usage_limit_per_user: number
  valid_from: string
  valid_until: string
  applicable_category: string | null
  category_name: string | null
  is_active: boolean
  is_valid_now: boolean
  created_at: string
  updated_at: string
}

export interface VoucherPayload {
  code: string
  name: string
  description?: string
  discount_type: DiscountType
  discount_value: number
  max_discount_amount: number | null
  min_order_amount: number
  total_usage_limit: number | null
  usage_limit_per_user: number
  valid_from: string
  valid_until: string
  applicable_category?: string | null
  is_active: boolean
}

export interface FlashSaleItem {
  id?: string
  variant: string
  product_id?: string
  product_name?: string
  product_slug?: string
  variant_sku?: string
  shop_id?: number
  shop_name?: string
  primary_image?: string | null
  original_price?: string
  sale_price: string
  quota: number
  sold_count: number
  remaining_quota?: number
}

export interface FlashSale {
  id: string
  name: string
  start_time: string
  end_time: string
  is_active: boolean
  status: 'upcoming' | 'ongoing' | 'ended'
  items: FlashSaleItem[]
  created_at: string
  updated_at: string
}

export interface FlashSalePayload {
  name: string
  start_time: string
  end_time: string
  is_active: boolean
  items: Array<Pick<FlashSaleItem, 'variant' | 'sale_price' | 'quota'>>
}
