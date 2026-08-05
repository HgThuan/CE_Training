<script setup lang="ts">
import { CheckCircleIcon } from '@heroicons/vue/24/outline'
import { onMounted, ref } from 'vue'

import FormMessage from '@/features/auth/components/FormMessage.vue'
import { getErrorMessage } from '@/features/auth/errors'
import { useAuthStore } from '@/stores/auth'

import { useNotifications } from '../composables/useNotifications'
import type { AppNotification } from '../types'

const authStore = useAuthStore()
const center = useNotifications(() => authStore.accessToken)
const { notifications, unreadCount, connected } = center
const loading = ref(true)
const errorMessage = ref('')

async function start(): Promise<void> {
  try {
    await center.start()
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
}

function destination(notification: AppNotification): string | null {
  const data = notification.data
  if (typeof data.conversation_id === 'string') {
    return authStore.user?.role === 'seller' ? '/seller/chat' : '/account/chat'
  }
  if (typeof data.order_id === 'string' && authStore.user?.role === 'customer') {
    return `/account/orders/${data.order_id}`
  }
  if (typeof data.shop_order_id === 'string' && authStore.user?.role === 'seller') {
    return '/seller/orders'
  }
  return null
}

onMounted(start)
</script>

<template>
  <main class="mx-auto max-w-4xl px-4 py-10 sm:px-6">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <p class="text-sm font-bold uppercase tracking-[0.18em] text-indigo-600">
          Notification center
        </p>
        <h1 class="mt-2 text-3xl font-black">Thông báo</h1>
        <p class="mt-2 text-sm text-slate-500">
          {{ connected ? 'Cập nhật realtime đang hoạt động' : 'Đang tự động đồng bộ định kỳ' }}
        </p>
      </div>
      <button
        class="inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold disabled:opacity-50"
        type="button"
        :disabled="!unreadCount"
        @click="center.markAllRead"
      >
        <CheckCircleIcon class="h-5 w-5" /> Đánh dấu tất cả đã đọc
      </button>
    </div>
    <FormMessage v-if="errorMessage" class="mt-5" :message="errorMessage" />
    <p v-if="loading" class="mt-6 rounded-2xl bg-white p-8">Đang tải thông báo…</p>
    <div v-else class="mt-6 overflow-hidden rounded-3xl border border-slate-200 bg-white">
      <article
        v-for="notification in notifications"
        :key="notification.id"
        class="border-b border-slate-100 p-5 last:border-b-0"
        :class="notification.is_read ? 'bg-white' : 'bg-indigo-50/70'"
      >
        <div class="flex gap-4">
          <span
            class="mt-2 h-2.5 w-2.5 shrink-0 rounded-full"
            :class="notification.is_read ? 'bg-slate-200' : 'bg-indigo-600'"
          />
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-start justify-between gap-2">
              <h2 class="font-black text-slate-900">{{ notification.title }}</h2>
              <time class="text-xs text-slate-500">{{
                new Date(notification.created_at).toLocaleString('vi-VN')
              }}</time>
            </div>
            <p class="mt-1 text-sm leading-6 text-slate-600">{{ notification.message }}</p>
            <div class="mt-3 flex gap-4 text-sm font-bold">
              <button
                v-if="!notification.is_read"
                class="text-indigo-700"
                type="button"
                @click="center.markRead(notification)"
              >
                Đánh dấu đã đọc
              </button>
              <RouterLink
                v-if="destination(notification)"
                class="text-slate-700 underline"
                :to="destination(notification) || '#'"
                @click="center.markRead(notification)"
                >Xem chi tiết</RouterLink
              >
            </div>
          </div>
        </div>
      </article>
      <p v-if="!notifications.length" class="p-12 text-center text-slate-500">
        Bạn chưa có thông báo nào.
      </p>
    </div>
  </main>
</template>
