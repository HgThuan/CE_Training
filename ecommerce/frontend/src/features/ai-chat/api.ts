import { http, refreshAuthSession } from '@/shared/lib/http'
import type { ApiResponse } from '@/shared/types/api'

import type {
  ChatConversation,
  ChatConversationDetail,
  ChatFeedback,
  ChatMessagePayload,
  ChatStreamEvent,
} from './types'

function apiUrl(path: string): string {
  const baseUrl = (import.meta.env.VITE_API_BASE_URL ?? '/api/v1').replace(/\/$/, '')
  return `${baseUrl}${path}`
}

const ACCESS_TOKEN_REFRESH_SKEW_SECONDS = 30

function accessTokenNeedsRefresh(token: string): boolean {
  try {
    const payload = token.split('.')[1]
    if (!payload) return false
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/')
    const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, '=')
    const claims = JSON.parse(atob(padded)) as { exp?: unknown }
    return (
      typeof claims.exp === 'number' &&
      claims.exp <= Date.now() / 1000 + ACCESS_TOKEN_REFRESH_SKEW_SECONDS
    )
  } catch {
    // The server remains authoritative for malformed, revoked, or opaque tokens.
    return false
  }
}

async function refreshTokenOrThrow(refreshAccessToken: () => Promise<string>): Promise<string> {
  try {
    return await refreshAccessToken()
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new Error('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại để tiếp tục.', {
      cause: error,
    })
  }
}

async function responseError(response: Response): Promise<Error> {
  if (response.status === 401) {
    return new Error('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại để tiếp tục.')
  }
  try {
    const payload = (await response.json()) as {
      message?: string
      detail?: string
      errors?: Record<string, string[]>
    }
    const fieldError = payload.errors
      ? Object.values(payload.errors)
          .flat()
          .find((value) => typeof value === 'string')
      : undefined
    return new Error(
      fieldError ?? payload.message ?? payload.detail ?? 'Không thể kết nối trợ lý AI.',
    )
  } catch {
    return new Error('Không thể kết nối trợ lý AI.')
  }
}

function parseEventBlock(block: string): ChatStreamEvent | null {
  const data = block
    .split('\n')
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).trimStart())
    .join('\n')
  if (!data) return null
  return JSON.parse(data) as ChatStreamEvent
}

export async function streamAssistantMessage(
  payload: ChatMessagePayload,
  accessToken: string | null,
  onEvent: (event: ChatStreamEvent) => void,
  signal?: AbortSignal,
  refreshAccessToken: () => Promise<string> = refreshAuthSession,
): Promise<void> {
  const request = (token: string | null) =>
    fetch(apiUrl('/ai/assistant/messages'), {
      method: 'POST',
      credentials: 'include',
      signal,
      headers: {
        Accept: 'text/event-stream',
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(payload),
    })

  let requestToken = accessToken
  if (requestToken && accessTokenNeedsRefresh(requestToken) && !signal?.aborted) {
    requestToken = await refreshTokenOrThrow(refreshAccessToken)
  }

  let response = await request(requestToken)
  if (response.status === 401 && requestToken && !signal?.aborted) {
    await response.body?.cancel()
    response = await request(await refreshTokenOrThrow(refreshAccessToken))
  }
  if (!response.ok) throw await responseError(response)
  if (!response.body) throw new Error('Trình duyệt không hỗ trợ phản hồi trực tuyến.')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    buffer += decoder.decode(value, { stream: !done }).replace(/\r\n/g, '\n')
    const blocks = buffer.split('\n\n')
    buffer = blocks.pop() ?? ''
    for (const block of blocks) {
      const event = parseEventBlock(block)
      if (event) onEvent(event)
    }
    if (done) break
  }
  if (buffer.trim()) {
    const event = parseEventBlock(buffer)
    if (event) onEvent(event)
  }
}

export const aiChatApi = {
  conversations: (guestToken?: string) =>
    http.get<ApiResponse<ChatConversation[]>>('/ai/assistant/conversations/', {
      params: guestToken ? { guest_token: guestToken } : undefined,
    }),
  conversation: (conversationId: string, guestToken?: string) =>
    http.get<ApiResponse<ChatConversationDetail>>(
      `/ai/assistant/conversations/${conversationId}/`,
      {
        params: guestToken ? { guest_token: guestToken } : undefined,
      },
    ),
  deleteConversation: (conversationId: string, guestToken?: string) =>
    http.delete<ApiResponse<null>>(`/ai/assistant/conversations/${conversationId}/`, {
      params: guestToken ? { guest_token: guestToken } : undefined,
    }),
  feedback: (
    messageId: string,
    payload: { guest_token?: string; rating: number; resolved?: boolean; comment?: string },
  ) =>
    http.post<ApiResponse<ChatFeedback>>(`/ai/assistant/messages/${messageId}/feedback`, payload),
}
