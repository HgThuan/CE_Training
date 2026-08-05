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
  CheckBadgeIcon
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
  <div class="flex min-h-screen bg-slate-50 text-slate-900">
    <!-- Sidebar -->
    <aside class="w-[240px] flex-shrink-0 border-r border-slate-800 flex flex-col bg-slate-950">
      <!-- Header -->
      <div class="flex items-center gap-3 px-6 py-5">
        <span class="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500 text-sm font-bold text-white">
          M
        </span>
        <span class="font-bold text-white tracking-wide">Admin console</span>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 overflow-y-auto px-4 py-2 space-y-6 scrollbar-hide pb-8">
        <!-- Main -->
        <div>
          <RouterLink
            to="/admin"
            end
            class="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
            active-class="!bg-indigo-600/20 !text-indigo-400"
          >
            <HomeIcon class="h-5 w-5" />
            Tổng quan
          </RouterLink>
        </div>

        <!-- Sản phẩm -->
        <div>
          <p class="mb-2 px-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Sản phẩm</p>
          <div class="space-y-1">
            <RouterLink
              to="/admin/products"
              class="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
              active-class="!bg-indigo-600/20 !text-indigo-400"
            >
              <CubeIcon class="h-5 w-5" /> Sản phẩm
            </RouterLink>
            <RouterLink
              to="/admin/categories"
              class="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
              active-class="!bg-indigo-600/20 !text-indigo-400"
            >
              <RectangleStackIcon class="h-5 w-5" /> Danh mục
            </RouterLink>
            <RouterLink
              to="/admin/brands"
              class="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
              active-class="!bg-indigo-600/20 !text-indigo-400"
            >
              <TagIcon class="h-5 w-5" /> Thương hiệu
            </RouterLink>
          </div>
        </div>

        <!-- Marketing -->
        <div>
          <p class="mb-2 px-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Marketing</p>
          <div class="space-y-1">
            <RouterLink
              to="/admin/vouchers"
              class="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
              active-class="!bg-indigo-600/20 !text-indigo-400"
            >
              <TicketIcon class="h-5 w-5" /> Voucher
            </RouterLink>
            <RouterLink
              to="/admin/flash-sales"
              class="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
              active-class="!bg-indigo-600/20 !text-indigo-400"
            >
              <BoltIcon class="h-5 w-5" /> Flash sale
            </RouterLink>
            <RouterLink
              to="/admin/banners"
              class="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
              active-class="!bg-indigo-600/20 !text-indigo-400"
            >
              <PhotoIcon class="h-5 w-5" /> Banner
            </RouterLink>
          </div>
        </div>

        <!-- Vận hành -->
        <div>
          <p class="mb-2 px-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Vận hành</p>
          <div class="space-y-1">
            <RouterLink
              to="/admin/orders"
              class="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
              active-class="!bg-indigo-600/20 !text-indigo-400"
            >
              <ClipboardDocumentListIcon class="h-5 w-5" /> Đơn hàng
            </RouterLink>
            <RouterLink
              to="/admin/disputes"
              class="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
              active-class="!bg-indigo-600/20 !text-indigo-400"
            >
              <ScaleIcon class="h-5 w-5" /> Tranh chấp
            </RouterLink>
            <RouterLink
              to="/admin/review-reports"
              class="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
              active-class="!bg-indigo-600/20 !text-indigo-400"
            >
              <ChatBubbleBottomCenterTextIcon class="h-5 w-5" /> Báo cáo review
            </RouterLink>
            <RouterLink
              to="/admin/operations"
              class="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
              active-class="!bg-indigo-600/20 !text-indigo-400"
            >
              <ChartBarSquareIcon class="h-5 w-5" /> Báo cáo
            </RouterLink>
          </div>
        </div>

        <!-- Người dùng -->
        <div>
          <p class="mb-2 px-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Người dùng</p>
          <div class="space-y-1">
            <RouterLink
              to="/admin/customers"
              class="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
              active-class="!bg-indigo-600/20 !text-indigo-400"
            >
              <UsersIcon class="h-5 w-5" /> Khách hàng
            </RouterLink>
            <RouterLink
              to="/admin/sellers"
              class="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
              active-class="!bg-indigo-600/20 !text-indigo-400"
            >
              <BuildingStorefrontIcon class="h-5 w-5" /> Seller
            </RouterLink>
            <RouterLink
              to="/admin/seller-applications"
              class="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
              active-class="!bg-indigo-600/20 !text-indigo-400"
            >
              <CheckBadgeIcon class="h-5 w-5" /> Duyệt seller
            </RouterLink>
          </div>
        </div>
      </nav>

      <!-- Footer / Logout -->
      <div class="border-t border-slate-800 p-4">
        <button
          @click="logout"
          class="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-slate-400 hover:bg-rose-500/10 hover:text-rose-400 transition-colors"
        >
          <ArrowLeftStartOnRectangleIcon class="h-5 w-5" />
          Đăng xuất
        </button>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 overflow-y-auto bg-slate-50">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.scrollbar-hide::-webkit-scrollbar {
  display: none;
}
.scrollbar-hide {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>
