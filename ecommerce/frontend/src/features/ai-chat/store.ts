import axios from 'axios'
import { defineStore } from 'pinia'
import { ref } from 'vue'

import { useAuthStore } from '@/stores/auth'
import { readBrowsingHistory } from '@/features/product/browsingHistory'

import { aiChatApi, streamChatTurn } from './api'
import type { ChatMessage, ChatStreamEvent } from './types'

const GUEST_TOKEN_KEY = 'mercato.ai-chat.guest-token'
const SESSION_KEY_PREFIX = 'mercato.ai-chat.session'

function randomToken(): string {
  if (typeof globalThis.crypto?.randomUUID === 'function') return globalThis.crypto.randomUUID()
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`
}

function currentGuestToken(): string {
  const stored = window.localStorage.getItem(GUEST_TOKEN_KEY)
  if (stored) return stored
  const token = randomToken()
  window.localStorage.setItem(GUEST_TOKEN_KEY, token)
  return token
}

export const useChatStore = defineStore('ai-shopping-chat', () => {
  const authStore = useAuthStore()
  const sessionId = ref<string | null>(null)
  const guestToken = ref(currentGuestToken())
  const messages = ref<ChatMessage[]>([])
  const isStreaming = ref(false)
  const isLoadingHistory = ref(false)
  const errorMessage = ref('')
  const historyError = ref('')
  const activeIdentity = ref('')
  let activeController: AbortController | null = null

  function identity(): string {
    return authStore.user ? `user:${authStore.user.id}` : 'guest'
  }

  function sessionStorageKey(owner = identity()): string {
    return `${SESSION_KEY_PREFIX}:${owner}`
  }

  function saveSession(): void {
    if (sessionId.value) {
      window.localStorage.setItem(sessionStorageKey(), sessionId.value)
    } else {
      window.localStorage.removeItem(sessionStorageKey())
    }
  }

  async function initialize(): Promise<void> {
    const nextIdentity = identity()
    if (activeIdentity.value === nextIdentity) return
    const previousIdentity = activeIdentity.value
    activeIdentity.value = nextIdentity

    if (previousIdentity === 'guest' && nextIdentity.startsWith('user:') && sessionId.value) {
      saveSession()
    } else {
      sessionId.value = window.localStorage.getItem(sessionStorageKey())
      messages.value = []
    }
    errorMessage.value = ''
    historyError.value = ''
    await loadHistory()
  }

  async function loadHistory(): Promise<void> {
    if (!sessionId.value || isLoadingHistory.value) return
    isLoadingHistory.value = true
    historyError.value = ''
    try {
      const response = await aiChatApi.history(sessionId.value, guestToken.value)
      messages.value = response.data.data
    } catch (error) {
      const status = axios.isAxiosError(error) ? error.response?.status : undefined
      if (status && [401, 403, 404].includes(status)) {
        sessionId.value = null
        messages.value = []
        saveSession()
      } else {
        historyError.value = 'Chưa thể tải lại cuộc trò chuyện. Phiên vẫn được giữ để bạn thử lại.'
      }
    } finally {
      isLoadingHistory.value = false
    }
  }

  function handleEvent(event: ChatStreamEvent, assistantId: string): void {
    if (event.type === 'session') {
      sessionId.value = event.session_id
      saveSession()
      return
    }
    const assistant = messages.value.find((message) => message.id === assistantId)
    if (event.type === 'delta' && assistant) {
      assistant.content += event.text
      return
    }
    if (event.type === 'error') {
      errorMessage.value = event.text
      if (assistant && !assistant.content) assistant.content = event.text
      return
    }
    if (event.type === 'done') {
      const index = messages.value.findIndex((message) => message.id === assistantId)
      if (index >= 0) messages.value[index] = event.message
    }
  }

  async function sendMessage(rawMessage: string): Promise<void> {
    const content = rawMessage.trim()
    if (!content || isStreaming.value) return
    errorMessage.value = ''
    const now = new Date().toISOString()
    const userMessage: ChatMessage = {
      id: `local-user-${Date.now()}`,
      role: 'user',
      content,
      attachments: [],
      created_at: now,
    }
    const assistantId = `local-assistant-${Date.now()}`
    messages.value.push(userMessage, {
      id: assistantId,
      role: 'assistant',
      content: '',
      attachments: [],
      created_at: now,
    })
    isStreaming.value = true
    const controller = new AbortController()
    activeController = controller
    try {
      await streamChatTurn(
        {
          ...(sessionId.value ? { session_id: sessionId.value } : {}),
          guest_token: guestToken.value,
          message: content,
          browsing_history: readBrowsingHistory(authStore.user?.id),
          channel: 'web',
        },
        authStore.accessToken,
        (event) => handleEvent(event, assistantId),
        controller.signal,
      )
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
      const message = error instanceof Error ? error.message : 'Không thể kết nối trợ lý AI.'
      errorMessage.value = message
      const assistant = messages.value.find((entry) => entry.id === assistantId)
      if (assistant && !assistant.content) assistant.content = message
    } finally {
      if (activeController === controller) {
        activeController = null
        isStreaming.value = false
      }
    }
  }

  function newConversation(): void {
    activeController?.abort()
    activeController = null
    sessionId.value = null
    messages.value = []
    errorMessage.value = ''
    historyError.value = ''
    isStreaming.value = false
    saveSession()
  }

  async function submitFeedback(messageId: string, rating: number): Promise<void> {
    const message = messages.value.find((entry) => entry.id === messageId)
    if (!message || message.role !== 'assistant' || message.id.startsWith('local-')) return
    try {
      const response = await aiChatApi.feedback(messageId, {
        guest_token: guestToken.value,
        rating,
        resolved: rating >= 4,
      })
      message.feedback = response.data.data
    } catch {
      errorMessage.value = 'Chưa thể gửi đánh giá. Bạn có thể thử lại sau.'
    }
  }

  return {
    sessionId,
    messages,
    isStreaming,
    isLoadingHistory,
    errorMessage,
    historyError,
    initialize,
    loadHistory,
    sendMessage,
    submitFeedback,
    newConversation,
  }
})
