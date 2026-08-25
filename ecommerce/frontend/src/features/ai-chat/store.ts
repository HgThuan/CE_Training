import axios from 'axios'
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { readBrowsingHistory } from '@/features/product/browsingHistory'
import { useAuthStore } from '@/stores/auth'

import { aiChatApi, streamAssistantMessage } from './api'
import type { AssistantStage, ChatConversation, ChatMessage, ChatStreamEvent } from './types'

const GUEST_TOKEN_KEY = 'mercato.ai-chat.guest-token'

function guestToken(): string {
  const stored = window.localStorage.getItem(GUEST_TOKEN_KEY)
  if (stored) return stored
  const token =
    typeof globalThis.crypto?.randomUUID === 'function'
      ? globalThis.crypto.randomUUID()
      : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`
  window.localStorage.setItem(GUEST_TOKEN_KEY, token)
  return token
}

export const useChatStore = defineStore('ai-shopping-assistant', () => {
  const authStore = useAuthStore()
  const conversationId = ref<string | null>(null)
  const conversations = ref<ChatConversation[]>([])
  const messages = ref<ChatMessage[]>([])
  const isStreaming = ref(false)
  const isLoadingHistory = ref(false)
  const errorMessage = ref('')
  const historyError = ref('')
  const activeStage = ref<AssistantStage | null>(null)
  const lastFailedMessage = ref('')
  const activeIdentity = ref('')
  const anonymousToken = ref(guestToken())
  let activeController: AbortController | null = null

  const canUseAssistant = computed(() => true)
  const ownerToken = computed(() => (authStore.isAuthenticated ? undefined : anonymousToken.value))

  async function initialize(): Promise<void> {
    const nextIdentity = authStore.user ? `user:${authStore.user.id}` : 'anonymous'
    if (activeIdentity.value === nextIdentity) return
    activeIdentity.value = nextIdentity
    resetLocalConversation()
    conversations.value = []
    await loadConversations()
  }

  async function loadConversations(): Promise<void> {
    isLoadingHistory.value = true
    historyError.value = ''
    try {
      const response = await aiChatApi.conversations(ownerToken.value)
      conversations.value = response.data.data
      if (!conversationId.value && conversations.value.length) {
        await selectConversation(conversations.value[0].id)
      }
    } catch {
      historyError.value = 'Chưa thể tải lịch sử hội thoại. Bạn có thể thử lại.'
    } finally {
      isLoadingHistory.value = false
    }
  }

  async function selectConversation(id: string): Promise<void> {
    if (!canUseAssistant.value || isStreaming.value) return
    isLoadingHistory.value = true
    historyError.value = ''
    try {
      const response = await aiChatApi.conversation(id, ownerToken.value)
      conversationId.value = id
      messages.value = response.data.data.messages
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 404) {
        conversations.value = conversations.value.filter((item) => item.id !== id)
        if (conversationId.value === id) resetLocalConversation()
      }
      historyError.value = 'Chưa thể mở cuộc trò chuyện này. Vui lòng thử lại.'
    } finally {
      isLoadingHistory.value = false
    }
  }

  function handleEvent(event: ChatStreamEvent, assistantId: string): void {
    if (event.type === 'conversation') {
      conversationId.value = event.conversation_id
      return
    }
    if (event.type === 'stage') {
      activeStage.value = event.stage
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
    lastFailedMessage.value = ''
    const now = new Date().toISOString()
    const localSuffix = `${Date.now()}-${Math.random().toString(36).slice(2)}`
    const assistantId = `local-assistant-${localSuffix}`
    messages.value.push(
      {
        id: `local-user-${localSuffix}`,
        role: 'user',
        content,
        attachments: [],
        created_at: now,
      },
      {
        id: assistantId,
        role: 'assistant',
        content: '',
        attachments: [],
        created_at: now,
      },
    )
    isStreaming.value = true
    activeStage.value = 'understanding'
    const controller = new AbortController()
    activeController = controller
    try {
      await streamAssistantMessage(
        {
          ...(conversationId.value ? { conversation_id: conversationId.value } : {}),
          ...(ownerToken.value ? { guest_token: ownerToken.value } : {}),
          message: content,
          browsing_history: readBrowsingHistory(authStore.user?.id),
          channel: 'web',
        },
        authStore.accessToken,
        (event) => {
          handleEvent(event, assistantId)
          if (event.type === 'error') lastFailedMessage.value = content
        },
        controller.signal,
      )
      await refreshConversationList()
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
      const message = error instanceof Error ? error.message : 'Không thể kết nối trợ lý AI.'
      errorMessage.value = message
      lastFailedMessage.value = content
      const assistant = messages.value.find((entry) => entry.id === assistantId)
      if (assistant && !assistant.content) assistant.content = message
    } finally {
      if (activeController === controller) {
        activeController = null
        isStreaming.value = false
        activeStage.value = null
      }
    }
  }

  async function refreshConversationList(): Promise<void> {
    try {
      conversations.value = (await aiChatApi.conversations(ownerToken.value)).data.data
    } catch {
      // The completed message remains usable even if refreshing the list fails.
    }
  }

  async function retryLastMessage(): Promise<void> {
    const content = lastFailedMessage.value
    if (!content) return
    const failedPair = messages.value.slice(-2)
    if (failedPair[0]?.id.startsWith('local-user-')) messages.value.splice(-2)
    await sendMessage(content)
  }

  function resetLocalConversation(): void {
    conversationId.value = null
    messages.value = []
    errorMessage.value = ''
    historyError.value = ''
    activeStage.value = null
    lastFailedMessage.value = ''
  }

  function newConversation(): void {
    activeController?.abort()
    activeController = null
    isStreaming.value = false
    resetLocalConversation()
  }

  async function deleteConversation(id: string): Promise<void> {
    await aiChatApi.deleteConversation(id, ownerToken.value)
    conversations.value = conversations.value.filter((item) => item.id !== id)
    if (conversationId.value === id) resetLocalConversation()
  }

  async function submitFeedback(messageId: string, rating: number): Promise<void> {
    const message = messages.value.find((entry) => entry.id === messageId)
    if (!message || message.role !== 'assistant' || message.id.startsWith('local-')) return
    try {
      const response = await aiChatApi.feedback(messageId, {
        ...(ownerToken.value ? { guest_token: ownerToken.value } : {}),
        rating,
        resolved: rating >= 4,
      })
      message.feedback = response.data.data
    } catch {
      errorMessage.value = 'Chưa thể gửi đánh giá. Bạn có thể thử lại sau.'
    }
  }

  return {
    conversationId,
    conversations,
    messages,
    isStreaming,
    isLoadingHistory,
    errorMessage,
    historyError,
    activeStage,
    lastFailedMessage,
    canUseAssistant,
    initialize,
    loadConversations,
    selectConversation,
    sendMessage,
    retryLastMessage,
    submitFeedback,
    newConversation,
    deleteConversation,
  }
})
