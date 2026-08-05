export type MessageType = 'TEXT' | 'IMAGE' | 'PRODUCT' | 'ORDER' | 'SYSTEM'

export interface MessageAttachment {
  id: string
  file_url: string
  mime_type: string
  size_bytes: number
  created_at: string
}

export interface ChatMessage {
  id: string
  conversation: string
  sender: number
  sender_name: string
  sender_role: 'customer' | 'seller' | 'admin'
  message_type: MessageType
  content: string
  product: string | null
  product_name: string | null
  product_slug: string | null
  shop_order: string | null
  shop_order_code: string | null
  client_message_id: string | null
  attachments: MessageAttachment[]
  created_at: string
}

export interface Conversation {
  id: string
  shop: number
  shop_name: string
  shop_slug: string
  shop_logo_url: string
  customer: number
  customer_name: string
  customer_avatar_url: string
  status: 'ACTIVE' | 'CLOSED'
  last_message_at: string | null
  unread_count: number
  last_message: ChatMessage | null
  created_at: string
}

export interface MessagePayload {
  message_type: MessageType
  content?: string
  product_id?: string
  shop_order_id?: string
  client_message_id: string
  attachments?: Array<{ file_url: string; mime_type: string; size_bytes: number }>
}
