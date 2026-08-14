<script setup lang="ts">
import {
  ArrowLeftStartOnRectangleIcon,
  Bars3Icon,
  BoltIcon,
  BuildingStorefrontIcon,
  ChartBarSquareIcon,
  ChatBubbleBottomCenterTextIcon,
  ClipboardDocumentListIcon,
  CubeIcon,
  HomeIcon,
  PhotoIcon,
  RectangleStackIcon,
  ScaleIcon,
  ShieldCheckIcon,
  TagIcon,
  TicketIcon,
  UsersIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'
import { computed, ref, watch } from 'vue'
import type { Component } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()
const mobileMenuOpen = ref(false)
const loggingOut = ref(false)

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
    items: [{ label: 'Tổng quan', to: '/admin', icon: HomeIcon, exact: true }],
  },
  {
    label: 'Sản phẩm',
    items: [
      { label: 'Sản phẩm', to: '/admin/products', icon: CubeIcon },
      { label: 'Danh mục', to: '/admin/categories', icon: RectangleStackIcon },
      { label: 'Thương hiệu', to: '/admin/brands', icon: TagIcon },
    ],
  },
  {
    label: 'Marketing',
    items: [
      { label: 'Voucher', to: '/admin/vouchers', icon: TicketIcon },
      { label: 'Flash sale', to: '/admin/flash-sales', icon: BoltIcon },
      { label: 'Banner', to: '/admin/banners', icon: PhotoIcon },
    ],
  },
  {
    label: 'Vận hành',
    items: [
      { label: 'Đơn hàng', to: '/admin/orders', icon: ClipboardDocumentListIcon },
      { label: 'Tranh chấp', to: '/admin/disputes', icon: ScaleIcon },
      {
        label: 'Báo cáo đánh giá',
        to: '/admin/review-reports',
        icon: ChatBubbleBottomCenterTextIcon,
      },
      { label: 'Báo cáo hệ thống', to: '/admin/operations', icon: ChartBarSquareIcon },
    ],
  },
  {
    label: 'Người dùng',
    items: [
      { label: 'Khách hàng', to: '/admin/customers', icon: UsersIcon },
      { label: 'Nhà bán hàng', to: '/admin/sellers', icon: BuildingStorefrontIcon },
      { label: 'Vai trò & quyền', to: '/admin/roles', icon: ShieldCheckIcon },
    ],
  },
]

const adminName = computed(() => authStore.user?.full_name || 'Quản trị viên')
const adminInitial = computed(() => adminName.value.trim().charAt(0).toUpperCase() || 'A')

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
        class="fixed inset-0 z-40 bg-slate-950/45 backdrop-blur-[2px] lg:hidden"
        aria-label="Đóng menu quản trị"
        @click="mobileMenuOpen = false"
      />
    </Transition>

    <aside
      class="fixed inset-y-0 left-0 z-50 flex w-[280px] -translate-x-full flex-col border-r border-slate-200 bg-white shadow-xl transition-transform duration-300 ease-out lg:sticky lg:top-0 lg:h-screen lg:translate-x-0 lg:shadow-none"
      :class="{ 'translate-x-0': mobileMenuOpen }"
      aria-label="Điều hướng quản trị"
    >
      <div class="flex h-20 shrink-0 items-center gap-3 border-b border-slate-100 px-5">
        <span
          class="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-700 text-sm font-black text-white shadow-md shadow-indigo-200"
          aria-hidden="true"
        >
          M
        </span>
        <div class="min-w-0 flex-1">
          <p class="truncate text-base font-black tracking-tight text-slate-900">Mercato</p>
          <p class="text-[11px] font-bold uppercase tracking-[0.18em] text-indigo-600">
            Admin Console
          </p>
        </div>
        <button
          type="button"
          class="rounded-lg p-2 text-slate-500 hover:bg-slate-100 hover:text-slate-900 lg:hidden"
          aria-label="Đóng menu"
          @click="mobileMenuOpen = false"
        >
          <XMarkIcon class="h-5 w-5" />
        </button>
      </div>

      <nav class="scrollbar-thin flex-1 space-y-5 overflow-y-auto px-3 py-5">
        <section v-for="group in navigation" :key="group.label || 'overview'">
          <p
            v-if="group.label"
            class="mb-1.5 px-3 text-[11px] font-bold uppercase tracking-[0.14em] text-slate-400"
          >
            {{ group.label }}
          </p>
          <div class="space-y-1">
            <RouterLink
              v-for="item in group.items"
              :key="item.to"
              :to="item.to"
              :exact-active-class="item.exact ? 'admin-nav-active' : undefined"
              :active-class="item.exact ? undefined : 'admin-nav-active'"
              class="group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-950"
            >
              <component
                :is="item.icon"
                class="h-5 w-5 shrink-0 text-slate-400 transition-colors group-hover:text-slate-700"
                aria-hidden="true"
              />
              <span>{{ item.label }}</span>
            </RouterLink>
          </div>
        </section>
      </nav>

      <div class="shrink-0 border-t border-slate-100 p-3">
        <div class="mb-2 flex items-center gap-3 rounded-xl bg-slate-50 p-3">
          <img
            v-if="authStore.user?.avatar_url"
            :src="authStore.user.avatar_url"
            :alt="`Ảnh đại diện của ${adminName}`"
            class="h-9 w-9 rounded-full object-cover ring-2 ring-white"
          />
          <span
            v-else
            class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-sm font-black text-indigo-700"
            aria-hidden="true"
          >
            {{ adminInitial }}
          </span>
          <div class="min-w-0">
            <p class="truncate text-sm font-bold text-slate-800">{{ adminName }}</p>
            <p class="truncate text-xs text-slate-500">{{ authStore.user?.email }}</p>
          </div>
        </div>
        <button
          type="button"
          class="flex w-full items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold text-rose-700 transition-colors hover:bg-rose-50 hover:text-rose-800 disabled:cursor-wait disabled:opacity-60"
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
        class="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-slate-200 bg-white/90 px-4 backdrop-blur lg:hidden"
      >
        <button
          type="button"
          class="rounded-xl border border-slate-200 bg-white p-2.5 text-slate-700 shadow-sm"
          aria-label="Mở menu quản trị"
          :aria-expanded="mobileMenuOpen"
          @click="mobileMenuOpen = true"
        >
          <Bars3Icon class="h-5 w-5" />
        </button>
        <div>
          <p class="text-sm font-black text-slate-900">Mercato Admin</p>
          <p class="text-xs text-slate-500">Không gian quản trị</p>
        </div>
      </header>

      <main class="min-h-[calc(100vh-4rem)] px-4 py-6 sm:px-6 lg:min-h-screen lg:px-8 lg:py-8">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style scoped>
.admin-nav-active {
  background: rgb(238 242 255);
  color: rgb(67 56 202);
  box-shadow: inset 3px 0 0 rgb(79 70 229);
}

.admin-nav-active :deep(svg) {
  color: rgb(79 70 229);
}

.scrollbar-thin {
  scrollbar-color: rgb(203 213 225) transparent;
  scrollbar-width: thin;
}
</style>
