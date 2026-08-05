<script setup lang="ts">
import { PaperAirplaneIcon, PhotoIcon } from '@heroicons/vue/24/outline'
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import FormMessage from '@/features/auth/components/FormMessage.vue'
import { getErrorMessage } from '@/features/auth/errors'
import { useAuthStore } from '@/stores/auth'

import { chatApi } from '../api'
import { useChatSocket } from '../composables/useChatSocket'
import type { ChatMessage, Conversation, MessagePayload } from '../types'

const route = useRoute()
const authStore = useAuthStore()
const conversations = ref<Conversation[]>([])
const activeConversation = ref<Conversation | null>(null)
const messages = ref<ChatMessage[]>([])
const content = ref('')
const imageUrl = ref('')
const loading = ref(true)
const sending = ref(false)
const errorMessage = ref('')
const messageList = ref<HTMLElement | null>(null)
const contextProductId = computed(() =>
  typeof route.query.product === 'string' ? route.query.product : '',
)
const contextOrderId = computed(() =>
  typeof route.query.order === 'string' ? route.query.order : '',
)

const titleFor = (conversation: Conversation) =>
  authStore.user?.role === 'seller' ? conversation.customer_name : conversation.shop_name

const activeTitle = computed(() =>
  activeConversation.value ? titleFor(activeConversation.value) : 'Tin nhắn',
)

function appendMessage(message: ChatMessage): void {
  if (message.conversation !== activeConversation.value?.id) return
  if (!messages.value.some((item) => item.id === message.id)) messages.value.push(message)
  void nextTick(() => messageList.value?.scrollTo({ top: messageList.value.scrollHeight }))
  void chatApi.read(message.conversation, message.id)
}

const socket = useChatSocket(() => authStore.accessToken, appendMessage)

async function selectConversation(conversation: Conversation): Promise<void> {
  activeConversation.value = conversation
  errorMessage.value = ''
  socket.connect(conversation.id)
  try {
    messages.value = (await chatApi.messages(conversation.id)).data.data
    const last = messages.value.at(-1)
    await chatApi.read(conversation.id, last?.id)
    conversation.unread_count = 0
    await nextTick()
    messageList.value?.scrollTo({ top: messageList.value.scrollHeight })
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
}

async function load(): Promise<void> {
  loading.value = true
  try {
    const shopSlug = typeof route.query.shop === 'string' ? route.query.shop : ''
    if (shopSlug && authStore.user?.role === 'customer') await chatApi.open(shopSlug)
    conversations.value = (await chatApi.conversations()).data.data
    if (conversations.value.length) await selectConversation(conversations.value[0])
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
}

async function sendMessage(): Promise<void> {
  if (!activeConversation.value || (!content.value.trim() && !imageUrl.value.trim())) return
  const payload: MessagePayload = imageUrl.value.trim()
    ? {
        message_type: 'IMAGE',
        content: content.value.trim(),
        client_message_id: crypto.randomUUID(),
        attachments: [{ file_url: imageUrl.value.trim(), mime_type: 'image/webp', size_bytes: 1 }],
      }
    : {
        message_type: 'TEXT',
        content: content.value.trim(),
        client_message_id: crypto.randomUUID(),
      }
  sending.value = true
  errorMessage.value = ''
  try {
    // Always use REST API to send — the response contains the saved message
    // for immediate display. The WebSocket broadcast handles delivery to
    // the other participant in realtime.
    const saved = (await chatApi.send(activeConversation.value.id, payload)).data.data
    appendMessage(saved)
    content.value = ''
    imageUrl.value = ''
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    sending.value = false
  }
}

async function sendContext(type: 'PRODUCT' | 'ORDER', id: string): Promise<void> {
  if (!activeConversation.value || !id) return
  const payload: MessagePayload = {
    message_type: type,
    client_message_id: crypto.randomUUID(),
    ...(type === 'PRODUCT' ? { product_id: id } : { shop_order_id: id }),
  }
  sending.value = true
  try {
    const saved = (await chatApi.send(activeConversation.value.id, payload)).data.data
    appendMessage(saved)
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    sending.value = false
  }
}

function chooseImage(): void {
  imageUrl.value = window.prompt('URL ảnh')?.trim() ?? ''
}

onMounted(load)
</script>

<template>
  <main class="mx-auto max-w-7xl px-4 py-8 sm:px-6">
    <div class="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <p class="text-sm font-bold uppercase tracking-[0.18em] text-indigo-600">Realtime chat</p>
        <h1 class="mt-2 text-3xl font-black">Hội thoại</h1>
      </div>
      <span
        class="rounded-full px-3 py-1 text-xs font-bold"
        :class="
          socket.connected ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'
        "
      >
        {{ socket.connected ? 'Đang kết nối realtime' : 'Đang dùng chế độ dự phòng' }}
      </span>
    </div>
    <FormMessage v-if="errorMessage" class="mb-4" :message="errorMessage" />
    <p v-if="loading" class="rounded-2xl bg-white p-8">Đang tải hội thoại…</p>
    <div
      v-else-if="conversations.length"
      class="grid min-h-[620px] overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm lg:grid-cols-[320px_1fr]"
    >
      <aside class="border-b border-slate-200 lg:border-b-0 lg:border-r">
        <button
          v-for="conversation in conversations"
          :key="conversation.id"
          class="flex w-full items-center gap-3 border-b border-slate-100 p-4 text-left hover:bg-slate-50"
          :class="activeConversation?.id === conversation.id ? 'bg-indigo-50' : ''"
          type="button"
          @click="selectConversation(conversation)"
        >
          <span
            class="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-indigo-100 font-black text-indigo-700"
          >
            {{ titleFor(conversation).slice(0, 1).toUpperCase() }}
          </span>
          <span class="min-w-0 flex-1">
            <span class="block truncate font-bold">{{ titleFor(conversation) }}</span>
            <span class="block truncate text-xs text-slate-500">{{
              conversation.last_message?.content || 'Bắt đầu trò chuyện'
            }}</span>
          </span>
          <span
            v-if="conversation.unread_count"
            class="rounded-full bg-rose-600 px-2 py-0.5 text-xs font-bold text-white"
            >{{ conversation.unread_count }}</span
          >
        </button>
      </aside>
      <section class="flex min-h-[620px] flex-col">
        <header class="border-b border-slate-200 px-5 py-4">
          <h2 class="font-black">{{ activeTitle }}</h2>
        </header>
        <div ref="messageList" class="flex-1 space-y-3 overflow-y-auto bg-slate-50 p-5">
          <article
            v-for="message in messages"
            :key="message.id"
            class="flex"
            :class="message.sender === authStore.user?.id ? 'justify-end' : 'justify-start'"
          >
            <div
              class="max-w-[78%] rounded-2xl px-4 py-3 text-sm shadow-sm"
              :class="
                message.sender === authStore.user?.id
                  ? 'bg-indigo-600 text-white'
                  : 'bg-white text-slate-800'
              "
            >
              <p v-if="message.content" class="whitespace-pre-wrap">{{ message.content }}</p>
              <img
                v-for="attachment in message.attachments"
                :key="attachment.id"
                class="mt-2 max-h-72 rounded-xl object-contain"
                :src="attachment.file_url"
                alt="Ảnh trong hội thoại"
              />
              <RouterLink
                v-if="message.product_slug"
                class="mt-2 block rounded-lg bg-black/10 p-2 font-bold underline"
                :to="{ name: 'product-detail', params: { slug: message.product_slug } }"
              >
                Sản phẩm: {{ message.product_name }}
              </RouterLink>
              <p v-if="message.shop_order_code" class="mt-2 rounded-lg bg-black/10 p-2 font-bold">
                Đơn {{ message.shop_order_code }}
              </p>
              <time class="mt-1 block text-[11px] opacity-70">{{
                new Date(message.created_at).toLocaleString('vi-VN')
              }}</time>
            </div>
          </article>
        </div>
        <form class="border-t border-slate-200 p-4" @submit.prevent="sendMessage">
          <div v-if="contextProductId || contextOrderId" class="mb-2 flex flex-wrap gap-2">
            <button
              v-if="contextProductId"
              class="rounded-lg bg-indigo-50 px-3 py-1.5 text-xs font-bold text-indigo-700"
              type="button"
              @click="sendContext('PRODUCT', contextProductId)"
            >
              Gửi sản phẩm đang xem
            </button>
            <button
              v-if="contextOrderId"
              class="rounded-lg bg-indigo-50 px-3 py-1.5 text-xs font-bold text-indigo-700"
              type="button"
              @click="sendContext('ORDER', contextOrderId)"
            >
              Gửi đơn hàng này
            </button>
          </div>
          <div
            v-if="imageUrl"
            class="mb-2 flex items-center gap-2 rounded-xl bg-indigo-50 px-3 py-2 text-xs"
          >
            <PhotoIcon class="h-4 w-4" /> Ảnh: <span class="truncate">{{ imageUrl }}</span>
            <button class="ml-auto font-bold" type="button" @click="imageUrl = ''">Bỏ</button>
          </div>
          <div class="flex gap-2">
            <input
              v-model.trim="content"
              class="min-w-0 flex-1 rounded-xl border border-slate-300 px-4 py-3"
              placeholder="Nhập tin nhắn…"
            />
            <button
              class="rounded-xl border border-slate-300 px-3"
              type="button"
              title="Gửi ảnh bằng URL"
              @click="chooseImage"
            >
              <PhotoIcon class="h-5 w-5" />
            </button>
            <button
              class="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 font-bold text-white disabled:opacity-50"
              :disabled="sending"
              type="submit"
            >
              <PaperAirplaneIcon class="h-5 w-5" /> Gửi
            </button>
          </div>
        </form>
      </section>
    </div>
    <div v-else class="rounded-3xl border border-dashed border-slate-300 bg-white p-12 text-center">
      <h2 class="text-xl font-black">Chưa có hội thoại</h2>
      <p class="mt-2 text-slate-600">Khách hàng có thể bắt đầu chat từ trang sản phẩm của shop.</p>
    </div>
  </main>
</template>
