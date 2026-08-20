import type { ProductCompareData, PublicProductListItem } from '@/features/product/types'

export interface ProductCardAttachment {
  type: 'product_card'
  product_id: string
  product: PublicProductListItem
  match?: {
    product_id?: string
    kind: 'exact' | 'alternative'
    matched_terms: string[]
    missing_terms: string[]
  }
}

export interface CompareTableAttachment {
  type: 'compare_table'
  product_ids: string[]
  comparison: ProductCompareData
}

export type ChatAttachment = ProductCardAttachment | CompareTableAttachment

export interface ChatMessage {
  id: string
  session_id?: string
  role: 'user' | 'assistant'
  content: string
  attachments: ChatAttachment[]
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
}
