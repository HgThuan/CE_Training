export interface StatusHistory {
  id: string
  from_status: string
  to_status: string
  reason: string
  created_at: string
}

import type { Review } from '@/features/after-sales/types'

export interface OrderItem {
  id: string
  product_name: string
  variant_name: string
  sku: string
  quantity: number
  line_total: string
  review?: Pick<Review, 'id' | 'rating' | 'content' | 'editable_until' | 'status' | 'media'>
}

export interface ShopOrder {
  id: string
  shop_order_code: string
  shop_name: string
  shop_slug: string
  fulfillment_status: string
  total_amount: string
  cod_collected_at: string | null
  items: OrderItem[]
  status_history: StatusHistory[]
  order_code?: string
  payment_method?: string
  payment_status?: string
  customer_email?: string
}

export interface CommerceOrder {
  id: string
  order_code: string
  grand_total: string
  payment_status: string
  payment_method: string
  placed_at: string
  shop_orders: ShopOrder[]
}

export interface CheckoutPreview {
  shops: Array<{
    shop_id: number
    shop_name: string
    subtotal: string
    shipping_fee: string
    total: string
  }>
  subtotal: string
  discount: string
  shipping_total: string
  total: string
}
