<script setup lang="ts">
import {
  ArrowLeftStartOnRectangleIcon,
  HeartIcon,
  ChatBubbleLeftRightIcon,
  ClipboardDocumentListIcon,
  ShoppingBagIcon,
  UserCircleIcon,
} from '@heroicons/vue/24/outline'
import { RouterView, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()

async function logout(): Promise<void> {
  await authStore.logout()
  await router.replace('/auth/login')
}
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <header class="border-b border-slate-200 bg-white">
      <div class="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
        <RouterLink class="flex items-center gap-3 font-black" to="/">
          <span class="grid h-10 w-10 place-items-center rounded-2xl bg-indigo-600 text-white"
            >M</span
          >
          Mercato
        </RouterLink>
        <nav class="flex items-center gap-1 text-sm font-bold">
          <RouterLink
            class="inline-flex items-center gap-2 rounded-xl px-3 py-2 text-slate-600 hover:bg-slate-100"
            to="/account/chat"
          >
            <ChatBubbleLeftRightIcon class="h-5 w-5" />
            <span class="hidden sm:inline">Chat</span>
          </RouterLink>
          <RouterLink
            class="inline-flex items-center gap-2 rounded-xl px-3 py-2 text-slate-600 hover:bg-slate-100"
            to="/products"
          >
            <ShoppingBagIcon class="h-5 w-5" />
            <span class="hidden sm:inline">Mua sắm</span>
          </RouterLink>
          <RouterLink
            class="inline-flex items-center gap-2 rounded-xl px-3 py-2 text-slate-600 hover:bg-slate-100"
            to="/wishlist"
          >
            <HeartIcon class="h-5 w-5" />
            <span class="hidden sm:inline">Yêu thích</span>
          </RouterLink>
          <RouterLink
            class="inline-flex items-center gap-2 rounded-xl px-3 py-2 text-slate-600 hover:bg-slate-100"
            active-class="!bg-indigo-50 !text-indigo-700"
            to="/account/orders"
          >
            <ClipboardDocumentListIcon class="h-5 w-5" />
            <span class="hidden sm:inline">Đơn hàng</span>
          </RouterLink>
          <RouterLink
            class="inline-flex items-center gap-2 rounded-xl px-3 py-2 text-slate-600 hover:bg-slate-100"
            to="/account/profile"
          >
            <UserCircleIcon class="h-5 w-5" />
            <span class="hidden sm:inline">Tài khoản</span>
          </RouterLink>
          <button
            class="grid h-10 w-10 place-items-center rounded-xl text-slate-500 hover:bg-rose-50 hover:text-rose-700"
            type="button"
            aria-label="Đăng xuất"
            @click="logout"
          >
            <ArrowLeftStartOnRectangleIcon class="h-5 w-5" />
          </button>
        </nav>
      </div>
    </header>
    <RouterView />
  </div>
</template>
