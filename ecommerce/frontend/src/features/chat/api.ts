import { http } from '@/shared/lib/http'
import type { ApiResponse } from '@/shared/types/api'

import type { ChatMessage, Conversation, MessagePayload } from './types'

export const chatApi = {
  conversations: () => http.get<ApiResponse<Conversation[]>>('/conversations'),
  open: (shopSlug: string) =>
    http.post<ApiResponse<Conversation>>('/conversations', { shop_slug: shopSlug }),
  messages: (conversationId: string) =>
    http.get<ApiResponse<ChatMessage[]>>(`/conversations/${conversationId}/messages`, {
      params: { page_size: 100 },
    }),
  send: (conversationId: string, payload: MessagePayload) =>
    http.post<ApiResponse<ChatMessage>>(`/conversations/${conversationId}/messages`, payload),
  read: (conversationId: string, messageId?: string) =>
    http.post<ApiResponse<{ last_read_message_id: string | null }>>(
      `/conversations/${conversationId}/read`,
      messageId ? { message_id: messageId } : {},
    ),
}
