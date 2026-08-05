import type { ShopOrder } from '@/features/order/types'

export interface ReviewMedia {
  id: string
  media_type: 'IMAGE' | 'VIDEO'
  file_url: string
}

export interface ReviewReply {
  id: string
  seller_name: string
  content: string
  updated_at: string
}

export interface Review {
  id: string
  order_item: string
  product: string
  product_name: string
  order_code: string
  customer_name: string
  rating: number
  content: string
  status: string
  is_verified_purchase: boolean
  editable_until: string | null
  media: ReviewMedia[]
  reply?: ReviewReply
  created_at: string
}

export interface ReturnRequestItem {
  id: string
  order_item: string
  product_name: string
  variant_name: string
  quantity: number
  requested_refund_amount: string
  approved_refund_amount: string | null
}

export interface ReturnRequest {
  id: string
  shop_order: string
  shop_order_code: string
  shop_name: string
  customer_email: string
  status: string
  reason_code: string
  reason_detail: string
  seller_response: string
  requested_at: string
  items: ReturnRequestItem[]
  media: ReviewMedia[]
}

export interface Dispute {
  id: string
  status: string
  decision: string | null
  decision_note: string
  refund_amount: string | null
  assigned_admin_email: string | null
  return_request: ReturnRequest
  evidence: Array<{
    id: string
    submitted_by_email: string
    content: string
    file_url: string
    created_at: string
  }>
}

export interface SellerCustomer {
  id: number
  email: string
  full_name: string
  order_count: number
  total_spent: string
  last_order_at: string
}

export type SellerCustomerOrder = ShopOrder

export interface ReviewReport {
  id: string
  review: Review
  reporter_email: string
  reason_code: string
  reason_detail: string
  status: string
  created_at: string
}
