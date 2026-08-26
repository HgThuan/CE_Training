export type VoucherScope = 'platform' | 'shop'
export type DiscountType = 'percent' | 'fixed' | 'freeship' | 'percentage' | 'fixed_amount'

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
  issuer_type: VoucherScope
  issuer_id: number | null
  value: string
  min_order_value: string
  total_quantity: number | null
  remaining_quantity: number | null
  per_user_limit: number
  start_time: string
  end_time: string
  collect_type: 'manual' | 'auto'
  stackable_with: VoucherScope[]
  applicable_scope: { shop_ids?: number[]; category_ids?: string[] } | null
  issued_quantity: number | null
  is_collected?: boolean
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
  collect_type: 'manual' | 'auto'
  stackable_with: VoucherScope[]
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
  shop_slug?: string
  primary_image?: string | null
  original_price?: string
  sale_price: string
  quota: number
  sold_count: number
  remaining_quota?: number
  category_id?: string
  category_name?: string
  available_stock?: number
}

export interface FlashSaleCatalogVariant {
  id: string
  sku: string
  name: string | null
  sale_price: string
  available_stock: number
  product_id: string
  product_name: string
  category_id: string
  category_name: string
  shop_id: number
  shop_name: string
  primary_image: string | null
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

export type UserVoucherStatus = 'saved' | 'pending_use' | 'used' | 'expired'

export interface UserVoucher {
  id: string
  campaign: Voucher
  status: UserVoucherStatus
  claimed_at: string
  used_at: string | null
  order_id: string | null
  checkout_token: string | null
  pending_expires_at: string | null
}

export interface CheckoutVoucher extends UserVoucher {
  is_eligible: boolean
  reason: string
  estimated_discount: string
}

export interface CheckoutVoucherList {
  results: CheckoutVoucher[]
  best_voucher_id: string | null
}
