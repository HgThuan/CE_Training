import type { ProductCompareData, PublicProductListItem } from '@/features/product/types'

export interface ProductCardAttachment {
  type: 'product_card'
  product_id: string
  product: PublicProductListItem
  match?: {
    product_id?: string
    kind: 'exact' | 'alternative' | 'personalized'
    matched_terms: string[]
    missing_terms: string[]
  }
}

export interface CompareTableAttachment {
  type: 'compare_table'
  product_ids: string[]
  comparison: ProductCompareData
}

export interface OrderSupportItem {
  id: string
  name: string
  variant: string
  quantity: number
}

export interface OrderSupportShop {
  id: string
  shop_order_code: string
  shop_name: string
  fulfillment_status: string
  fulfillment_status_label: string
  shipping_method: string
  estimated_delivery_at: string | null
  last_status_at: string
  return_eligible: boolean
  return_deadline: string | null
  items: OrderSupportItem[]
  return_requests: Array<{
    id: string
    status: string
    status_label: string
    requested_at: string
  }>
}

export interface OrderSupportAttachment {
  type: 'order_card'
  order: {
    id: string
    order_code: string
    placed_at: string
    grand_total: string
    currency: string
    payment_status: string
    payment_status_label: string
    payment_method: string
    payment_method_label: string
    shop_orders: OrderSupportShop[]
  }
}

export interface PromotionAttachment {
  type: 'promotion_card'
  promotion: {
    id: string
    code: string
    name: string
    description: string
    shop_name: string
    discount_type: 'percent' | 'fixed' | 'freeship'
    discount_value: string
    max_discount_amount: string | null
    min_order_amount: string
    valid_until: string
    remaining_quantity: number | null
    saved: boolean
  }
}

export interface QuickActionsAttachment {
  type: 'quick_actions'
  actions: Array<{
    label: string
    kind: 'reply' | 'link'
    value: string
  }>
}

export interface HandoffAttachment {
  type: 'handoff_card'
  handoff: {
    id: string
    status: string
    status_label: string
    channel: string
  }
}

export type ChatAttachment =
  | ProductCardAttachment
  | CompareTableAttachment
  | OrderSupportAttachment
  | PromotionAttachment
  | QuickActionsAttachment
  | HandoffAttachment

export interface ChatFeedback {
  rating: number
  resolved: boolean | null
  comment: string
}

export interface ChatMessage {
  id: string
  session_id?: string
  role: 'user' | 'assistant'
  content: string
  attachments: ChatAttachment[]
  feedback?: ChatFeedback | null
  created_at: string
}

export type ChatStreamEvent =
  | { type: 'session'; session_id: string }
  | { type: 'delta'; text: string }
  | { type: 'error'; text: string; code?: string }
  | { type: 'done'; message: ChatMessage }

export interface ChatTurnPayload {
  session_id?: string
  guest_token: string
  message: string
  browsing_history?: string[]
  channel?: string
}
