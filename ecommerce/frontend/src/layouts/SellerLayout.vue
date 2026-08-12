<script setup lang="ts">
import {
  ArchiveBoxIcon,
  ArrowLeftStartOnRectangleIcon,
  ArrowPathIcon,
  Bars3Icon,
  BellIcon,
  BuildingStorefrontIcon,
  ChatBubbleBottomCenterTextIcon,
  ClipboardDocumentListIcon,
  CubeIcon,
  EnvelopeIcon,
  HomeIcon,
  TicketIcon,
  UserIcon,
  UsersIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'
import { computed, ref, watch } from 'vue'
import type { Component } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'

import NotificationBell from '@/features/notification/components/NotificationBell.vue'
import { useAuthStore } from '@/stores/auth'

interface NavigationItem {
  label: string
  to: string
  icon: Component
  exact?: boolean
}

interface NavigationGroup {
  label: string
  items: NavigationItem[]
}

const navigation: NavigationGroup[] = [
  {
    label: '',
    items: [{ label: 'Tổng quan', to: '/seller', icon: HomeIcon, exact: true }],
  },
  {
    label: 'Sản phẩm & kho',
    items: [
      { label: 'Quản lý sản phẩm', to: '/seller/products', icon: CubeIcon },
      { label: 'Tồn kho', to: '/seller/inventory', icon: ArchiveBoxIcon },
    ],
  },
  {
    label: 'Bán hàng',
    items: [
      { label: 'Đơn hàng', to: '/seller/orders', icon: ClipboardDocumentListIcon },
      { label: 'Trả hàng', to: '/seller/returns', icon: ArrowPathIcon },
      { label: 'Khuyến mãi', to: '/seller/promotions', icon: TicketIcon },
    ],
  },
  {
    label: 'Khách hàng',
    items: [
      { label: 'Tin nhắn', to: '/seller/chat', icon: EnvelopeIcon },
      { label: 'Khách hàng', to: '/seller/customers', icon: UsersIcon },
      { label: 'Đánh giá', to: '/seller/reviews', icon: ChatBubbleBottomCenterTextIcon },
    ],
  },
  {
    label: 'Cửa hàng & tài khoản',
    items: [
      { label: 'Hồ sơ gian hàng', to: '/seller/shop', icon: BuildingStorefrontIcon },
      { label: 'Hồ sơ cá nhân', to: '/seller/profile', icon: UserIcon },
      { label: 'Thông báo', to: '/seller/notifications', icon: BellIcon },
    ],
  },
]

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()
const mobileMenuOpen = ref(false)
const loggingOut = ref(false)

const sellerName = computed(() => authStore.user?.full_name || 'Nhà bán hàng')
const sellerInitial = computed(() => sellerName.value.trim().charAt(0).toUpperCase() || 'S')
const contentClass = computed(() =>
  route.name === 'seller-home' ? 'px-4 py-6 sm:px-6 lg:px-8 lg:py-8' : '',
)

watch(
  () => route.fullPath,
  () => {
    mobileMenuOpen.value = false
  },
)

async function logout(): Promise<void> {
  loggingOut.value = true
  try {
    await authStore.logout()
    await router.replace('/auth/login')
  } finally {
    loggingOut.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-slate-50 font-sans text-slate-900 lg:flex">
    <Transition
      enter-active-class="transition-opacity duration-200"
      enter-from-class="opacity-0"
      leave-active-class="transition-opacity duration-200"
      leave-to-class="opacity-0"
    >
      <button
        v-if="mobileMenuOpen"
        type="button"
        class="fixed inset-0 z-40 bg-slate-950/60 lg:hidden"
        aria-label="Đóng menu Seller Center"
        @click="mobileMenuOpen = false"
      />
    </Transition>

    <aside
      class="fixed inset-y-0 left-0 z-50 flex w-[280px] -translate-x-full flex-col bg-slate-950 text-slate-300 shadow-xl transition-transform duration-300 ease-out lg:sticky lg:top-0 lg:h-screen lg:translate-x-0 lg:shadow-none"
      :class="{ 'translate-x-0': mobileMenuOpen }"
      aria-label="Điều hướng Seller Center"
    >
      <div class="flex h-20 shrink-0 items-center gap-3 border-b border-white/10 px-5">
        <span
          class="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-sm font-black text-white shadow-md shadow-slate-950/40"
          aria-hidden="true"
        >
          M
        </span>
        <div class="min-w-0 flex-1">
          <p class="truncate text-base font-black tracking-tight text-white">Mercato</p>
          <p class="text-[11px] font-bold uppercase tracking-[0.16em] text-indigo-300">
            Seller Center
          </p>
        </div>
        <button
          type="button"
          class="flex h-11 w-11 items-center justify-center rounded-xl text-slate-300 transition-colors hover:bg-white/10 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 lg:hidden"
          aria-label="Đóng menu"
          @click="mobileMenuOpen = false"
        >
          <XMarkIcon class="h-5 w-5" aria-hidden="true" />
        </button>
      </div>

      <nav class="seller-scrollbar flex-1 space-y-5 overflow-y-auto px-3 py-5">
        <section v-for="group in navigation" :key="group.label || 'overview'">
          <p
            v-if="group.label"
            class="mb-1.5 px-3 text-[11px] font-bold uppercase tracking-[0.12em] text-slate-500"
          >
            {{ group.label }}
          </p>
          <div class="space-y-1">
            <RouterLink
              v-for="item in group.items"
              :key="item.to"
              :to="item.to"
              :exact-active-class="item.exact ? 'seller-nav-active' : undefined"
              :active-class="item.exact ? undefined : 'seller-nav-active'"
              class="group flex min-h-11 items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold text-slate-300 transition-colors hover:bg-white/8 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
            >
              <component
                :is="item.icon"
                class="h-5 w-5 shrink-0 text-slate-500 transition-colors group-hover:text-slate-200"
                aria-hidden="true"
              />
              <span>{{ item.label }}</span>
            </RouterLink>
          </div>
        </section>
      </nav>

      <div class="shrink-0 border-t border-white/10 p-3">
        <RouterLink
          to="/seller/profile"
          class="mb-2 flex items-center gap-3 rounded-xl bg-white/5 p-3 transition-colors hover:bg-white/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
        >
          <img
            v-if="authStore.user?.avatar_url"
            :src="authStore.user.avatar_url"
            :alt="`Ảnh đại diện của ${sellerName}`"
            class="h-9 w-9 rounded-full object-cover ring-2 ring-slate-700"
          />
          <span
            v-else
            class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-indigo-500/20 text-sm font-black text-indigo-200"
            aria-hidden="true"
          >
            {{ sellerInitial }}
          </span>
          <span class="min-w-0">
            <span class="block truncate text-sm font-bold text-white">{{ sellerName }}</span>
            <span class="block truncate text-xs text-slate-400">{{ authStore.user?.email }}</span>
          </span>
        </RouterLink>
        <button
          type="button"
          class="flex min-h-11 w-full items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold text-slate-300 transition-colors hover:bg-rose-500/10 hover:text-rose-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-400 disabled:cursor-wait disabled:opacity-60"
          :disabled="loggingOut"
          @click="logout"
        >
          <ArrowLeftStartOnRectangleIcon class="h-5 w-5" aria-hidden="true" />
          {{ loggingOut ? 'Đang đăng xuất…' : 'Đăng xuất' }}
        </button>
      </div>
    </aside>

    <div class="min-w-0 flex-1">
      <header
        class="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-slate-200 bg-white px-4 lg:hidden"
      >
        <button
          type="button"
          class="flex h-11 w-11 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-700 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
          aria-label="Mở menu Seller Center"
          :aria-expanded="mobileMenuOpen"
          @click="mobileMenuOpen = true"
        >
          <Bars3Icon class="h-5 w-5" aria-hidden="true" />
        </button>
        <div class="min-w-0 flex-1">
          <p class="truncate text-sm font-black text-slate-900">Mercato Seller</p>
          <p class="truncate text-xs text-slate-500">Quản lý gian hàng</p>
        </div>
        <NotificationBell to="/seller/notifications" />
      </header>

      <main class="min-h-[calc(100vh-4rem)] lg:min-h-screen" :class="contentClass">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style scoped>
.seller-nav-active {
  background: rgb(67 56 202 / 0.3);
  color: white;
}

.seller-nav-active :deep(svg) {
  color: rgb(165 180 252);
}

.seller-scrollbar {
  scrollbar-color: rgb(71 85 105) transparent;
  scrollbar-width: thin;
}
</style>
