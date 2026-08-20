import { http } from '@/shared/lib/http'
import type { ApiResponse } from '@/shared/types/api'

import type { ChatMessage, ChatStreamEvent, ChatTurnPayload } from './types'

function apiUrl(path: string): string {
  const baseUrl = (import.meta.env.VITE_API_BASE_URL ?? '/api/v1').replace(/\/$/, '')
  return `${baseUrl}${path}`
}

async function responseError(response: Response): Promise<Error> {
  try {
    const payload = (await response.json()) as {
      message?: string
      detail?: string
      errors?: Record<string, string[]>
    }
    const fieldError = payload.errors
      ? Object.values(payload.errors).flat().find((value) => typeof value === 'string')
      : undefined
    return new Error(fieldError ?? payload.message ?? payload.detail ?? 'Không thể kết nối trợ lý AI.')
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

export async function streamChatTurn(
  payload: ChatTurnPayload,
  accessToken: string | null,
  onEvent: (event: ChatStreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(apiUrl('/chat/turn'), {
    method: 'POST',
    credentials: 'include',
    signal,
    headers: {
      Accept: 'text/event-stream',
      'Content-Type': 'application/json',
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    },
    body: JSON.stringify(payload),
  })
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
  history: (sessionId: string, guestToken: string) =>
    http.get<ApiResponse<ChatMessage[]>>(`/chat/sessions/${sessionId}/messages`, {
      params: { guest_token: guestToken },
    }),
}
