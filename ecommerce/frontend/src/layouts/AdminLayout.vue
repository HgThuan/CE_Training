<script setup lang="ts">
import {
  ArrowLeftStartOnRectangleIcon,
  BuildingStorefrontIcon,
  ClipboardDocumentListIcon,
  CubeIcon,
  HomeIcon,
  PhotoIcon,
  RectangleStackIcon,
  ScaleIcon,
  ChatBubbleBottomCenterTextIcon,
  TagIcon,
  TicketIcon,
  BoltIcon,
  UsersIcon,
  ChartBarSquareIcon,
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
  <div class="min-h-screen bg-slate-100">
    <header class="sticky top-0 z-30 border-b border-slate-800 bg-slate-950 text-white">
      <div class="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <RouterLink class="flex items-center gap-3" to="/admin">
          <span class="grid h-10 w-10 place-items-center rounded-2xl bg-indigo-500 font-black"
            >M</span
          >
          <div class="hidden sm:block">
            <p class="text-xs font-bold uppercase tracking-widest text-indigo-300">Mercato</p>
            <p class="text-sm font-black">Admin Console</p>
          </div>
        </RouterLink>
        <nav
          class="flex items-center gap-1 overflow-x-auto text-sm font-bold"
          aria-label="Admin navigation"
        >
          <RouterLink
            class="inline-flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-slate-300 hover:bg-white/10 hover:text-white"
            active-class="!bg-indigo-500 !text-white"
            to="/admin/orders"
          >
            <ClipboardDocumentListIcon class="h-4 w-4" />
            <span class="hidden lg:inline">Đơn hàng</span>
          </RouterLink>
          <RouterLink
            class="inline-flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-slate-300 hover:bg-white/10 hover:text-white"
            active-class="!bg-indigo-500 !text-white"
            to="/admin/operations"
          >
            <ChartBarSquareIcon class="h-4 w-4" />
            <span class="hidden lg:inline">Báo cáo</span>
          </RouterLink>
          <RouterLink
            class="inline-flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-slate-300 hover:bg-white/10 hover:text-white"
            active-class="!bg-indigo-500 !text-white"
            to="/admin/disputes"
          >
            <ScaleIcon class="h-4 w-4" />
            <span class="hidden lg:inline">Tranh chấp</span>
          </RouterLink>
          <RouterLink
            class="inline-flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-slate-300 hover:bg-white/10 hover:text-white"
            active-class="!bg-indigo-500 !text-white"
            to="/admin/review-reports"
            title="Báo cáo review"
          >
            <ChatBubbleBottomCenterTextIcon class="h-5 w-5" />
            <span class="hidden lg:inline">Báo cáo review</span>
          </RouterLink>
          <RouterLink
            class="inline-flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-slate-300 hover:bg-white/10 hover:text-white"
            active-class="!bg-indigo-500 !text-white"
            to="/admin/vouchers"
          >
            <TicketIcon class="h-4 w-4" />
            <span class="hidden lg:inline">Voucher</span>
          </RouterLink>
          <RouterLink
            class="inline-flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-slate-300 hover:bg-white/10 hover:text-white"
            active-class="!bg-indigo-500 !text-white"
            to="/admin/flash-sales"
          >
            <BoltIcon class="h-4 w-4" />
            <span class="hidden lg:inline">Flash Sale</span>
          </RouterLink>
          <RouterLink
            class="inline-flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-slate-300 hover:bg-white/10 hover:text-white"
            active-class="!bg-indigo-500 !text-white"
            to="/admin"
            end
          >
            <HomeIcon class="h-4 w-4" />
            <span class="hidden lg:inline">Tổng quan</span>
          </RouterLink>
          <RouterLink
            class="inline-flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-slate-300 hover:bg-white/10 hover:text-white"
            active-class="!bg-indigo-500 !text-white"
            to="/admin/products"
          >
            <CubeIcon class="h-4 w-4" />
            <span class="hidden lg:inline">Sản phẩm</span>
          </RouterLink>
          <RouterLink
            class="inline-flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-slate-300 hover:bg-white/10 hover:text-white"
            active-class="!bg-indigo-500 !text-white"
            to="/admin/categories"
          >
            <RectangleStackIcon class="h-4 w-4" />
            <span class="hidden lg:inline">Danh mục</span>
          </RouterLink>
          <RouterLink
            class="inline-flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-slate-300 hover:bg-white/10 hover:text-white"
            active-class="!bg-indigo-500 !text-white"
            to="/admin/brands"
          >
            <TagIcon class="h-4 w-4" />
            <span class="hidden lg:inline">Thương hiệu</span>
          </RouterLink>
          <RouterLink
            class="inline-flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-slate-300 hover:bg-white/10 hover:text-white"
            active-class="!bg-indigo-500 !text-white"
            to="/admin/customers"
          >
            <UsersIcon class="h-4 w-4" />
            <span class="hidden lg:inline">Khách hàng</span>
          </RouterLink>
          <RouterLink
            class="inline-flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-slate-300 hover:bg-white/10 hover:text-white"
            active-class="!bg-indigo-500 !text-white"
            to="/admin/sellers"
          >
            <BuildingStorefrontIcon class="h-4 w-4" />
            <span class="hidden lg:inline">Seller</span>
          </RouterLink>
          <RouterLink
            class="inline-flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-slate-300 hover:bg-white/10 hover:text-white"
            active-class="!bg-indigo-500 !text-white"
            to="/admin/banners"
          >
            <PhotoIcon class="h-4 w-4" />
            <span class="hidden lg:inline">Banner</span>
          </RouterLink>
          <RouterLink
            class="inline-flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-slate-300 hover:bg-white/10 hover:text-white"
            active-class="!bg-indigo-500 !text-white"
            to="/admin/vouchers"
          >
            <TicketIcon class="h-4 w-4" />
            <span class="hidden lg:inline">Voucher</span>
          </RouterLink>
          <RouterLink
            class="inline-flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-slate-300 hover:bg-white/10 hover:text-white"
            active-class="!bg-indigo-500 !text-white"
            to="/admin/flash-sales"
          >
            <BoltIcon class="h-4 w-4" />
            <span class="hidden lg:inline">Flash Sale</span>
          </RouterLink>
          <RouterLink
            class="inline-flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-slate-300 hover:bg-white/10 hover:text-white"
            active-class="!bg-indigo-500 !text-white"
            to="/admin/operations"
          >
            <ChartBarSquareIcon class="h-4 w-4" />
            <span class="hidden lg:inline">Báo cáo</span>
          </RouterLink>
          <RouterLink
            class="inline-flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-slate-300 hover:bg-white/10 hover:text-white"
            active-class="!bg-indigo-500 !text-white"
            to="/admin/disputes"
          >
            <ScaleIcon class="h-4 w-4" />
            <span class="hidden lg:inline">Tranh chấp</span>
          </RouterLink>
          <RouterLink
            class="inline-flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-slate-300 hover:bg-white/10 hover:text-white"
            active-class="!bg-indigo-500 !text-white"
            to="/admin/review-reports"
          >
            <ChatBubbleBottomCenterTextIcon class="h-4 w-4" />
            <span class="hidden lg:inline">Báo cáo review</span>
          </RouterLink>
          <button
            class="inline-flex shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-slate-300 hover:bg-rose-500/20 hover:text-rose-300"
            type="button"
            @click="logout"
          >
            <ArrowLeftStartOnRectangleIcon class="h-4 w-4" />
            <span class="hidden lg:inline">Đăng xuất</span>
          </button>
        </nav>
      </div>
    </header>
    <RouterView />
  </div>
</template>
