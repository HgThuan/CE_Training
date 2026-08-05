import { onBeforeUnmount, ref } from 'vue'

import { websocketUrl } from '@/shared/lib/websocket'

import type { ChatMessage, MessagePayload } from '../types'

interface ChatEvent {
  type: 'message' | 'error'
  data?: ChatMessage
  message?: string
}

export function useChatSocket(
  accessToken: () => string | null,
  onMessage: (message: ChatMessage) => void,
) {
  const connected = ref(false)
  let socket: WebSocket | null = null
  let reconnectTimer: number | null = null
  let reconnectAttempts = 0
  let activeConversationId = ''
  let disposed = false

  function scheduleReconnect(): void {
    if (disposed || !activeConversationId || reconnectTimer !== null) return
    const delay = Math.min(1_000 * 2 ** reconnectAttempts, 15_000)
    reconnectAttempts += 1
    reconnectTimer = window.setTimeout(() => {
      reconnectTimer = null
      connect(activeConversationId)
    }, delay)
  }

  function connect(conversationId: string): void {
    activeConversationId = conversationId
    socket?.close()
    const token = accessToken()
    if (!token) return
    socket = new WebSocket(websocketUrl(`/ws/chat/${conversationId}`, token))
    socket.onopen = () => {
      connected.value = true
      reconnectAttempts = 0
    }
    socket.onmessage = (event) => {
      const payload = JSON.parse(String(event.data)) as ChatEvent
      if (payload.type === 'message' && payload.data) onMessage(payload.data)
    }
    socket.onclose = () => {
      connected.value = false
      scheduleReconnect()
    }
    socket.onerror = () => socket?.close()
  }

  function send(payload: MessagePayload): boolean {
    if (!socket || socket.readyState !== WebSocket.OPEN) return false
    socket.send(JSON.stringify(payload))
    return true
  }

  function disconnect(): void {
    activeConversationId = ''
    if (reconnectTimer !== null) window.clearTimeout(reconnectTimer)
    reconnectTimer = null
    socket?.close()
    socket = null
    connected.value = false
  }

  onBeforeUnmount(() => {
    disposed = true
    disconnect()
  })

  return { connected, connect, disconnect, send }
}
