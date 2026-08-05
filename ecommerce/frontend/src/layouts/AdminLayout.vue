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
  <div class="flex min-h-screen bg-slate-50 text-slate-900 font-sans">
    <!-- Sidebar -->
    <aside class="w-[260px] flex-shrink-0 border-r border-slate-200 flex flex-col bg-white shadow-sm">
      <!-- Header -->
      <div class="flex items-center gap-3 px-6 py-6 border-b border-slate-100">
        <span class="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 text-sm font-bold text-white shadow-md shadow-indigo-200">
          M
        </span>
        <span class="font-black text-slate-800 text-lg tracking-tight">Admin console</span>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 overflow-y-auto px-4 py-4 space-y-6 scrollbar-hide pb-8">
        <!-- Main -->
        <div>
          <RouterLink
            to="/admin"
            end
            class="flex items-center gap-3 rounded-xl px-4 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
            active-class="!bg-indigo-50 !text-indigo-700 ring-1 ring-inset ring-indigo-100"
          >
            <HomeIcon class="h-5 w-5" />
            Tổng quan
          </RouterLink>
        </div>

        <!-- Sản phẩm -->
        <div>
          <p class="mb-2 px-4 text-xs font-bold text-slate-400 uppercase tracking-wider">Sản phẩm</p>
          <div class="space-y-1">
            <RouterLink
              to="/admin/products"
              class="flex items-center gap-3 rounded-xl px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
              active-class="!bg-indigo-50 !text-indigo-700 ring-1 ring-inset ring-indigo-100 font-semibold"
            >
              <CubeIcon class="h-5 w-5" /> Sản phẩm
            </RouterLink>
            <RouterLink
              to="/admin/categories"
              class="flex items-center gap-3 rounded-xl px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
              active-class="!bg-indigo-50 !text-indigo-700 ring-1 ring-inset ring-indigo-100 font-semibold"
            >
              <RectangleStackIcon class="h-5 w-5" /> Danh mục
            </RouterLink>
            <RouterLink
              to="/admin/brands"
              class="flex items-center gap-3 rounded-xl px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
              active-class="!bg-indigo-50 !text-indigo-700 ring-1 ring-inset ring-indigo-100 font-semibold"
            >
              <TagIcon class="h-5 w-5" /> Thương hiệu
            </RouterLink>
          </div>
        </div>

        <!-- Marketing -->
        <div>
          <p class="mb-2 px-4 text-xs font-bold text-slate-400 uppercase tracking-wider">Marketing</p>
          <div class="space-y-1">
            <RouterLink
              to="/admin/vouchers"
              class="flex items-center gap-3 rounded-xl px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
              active-class="!bg-indigo-50 !text-indigo-700 ring-1 ring-inset ring-indigo-100 font-semibold"
            >
              <TicketIcon class="h-5 w-5" /> Voucher
            </RouterLink>
            <RouterLink
              to="/admin/flash-sales"
              class="flex items-center gap-3 rounded-xl px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
              active-class="!bg-indigo-50 !text-indigo-700 ring-1 ring-inset ring-indigo-100 font-semibold"
            >
              <BoltIcon class="h-5 w-5" /> Flash sale
            </RouterLink>
            <RouterLink
              to="/admin/banners"
              class="flex items-center gap-3 rounded-xl px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
              active-class="!bg-indigo-50 !text-indigo-700 ring-1 ring-inset ring-indigo-100 font-semibold"
            >
              <PhotoIcon class="h-5 w-5" /> Banner
            </RouterLink>
          </div>
        </div>

        <!-- Vận hành -->
        <div>
          <p class="mb-2 px-4 text-xs font-bold text-slate-400 uppercase tracking-wider">Vận hành</p>
          <div class="space-y-1">
            <RouterLink
              to="/admin/orders"
              class="flex items-center gap-3 rounded-xl px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
              active-class="!bg-indigo-50 !text-indigo-700 ring-1 ring-inset ring-indigo-100 font-semibold"
            >
              <ClipboardDocumentListIcon class="h-5 w-5" /> Đơn hàng
            </RouterLink>
            <RouterLink
              to="/admin/disputes"
              class="flex items-center gap-3 rounded-xl px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
              active-class="!bg-indigo-50 !text-indigo-700 ring-1 ring-inset ring-indigo-100 font-semibold"
            >
              <ScaleIcon class="h-5 w-5" /> Tranh chấp
            </RouterLink>
            <RouterLink
              to="/admin/review-reports"
              class="flex items-center gap-3 rounded-xl px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
              active-class="!bg-indigo-50 !text-indigo-700 ring-1 ring-inset ring-indigo-100 font-semibold"
            >
              <ChatBubbleBottomCenterTextIcon class="h-5 w-5" /> Báo cáo review
            </RouterLink>
            <RouterLink
              to="/admin/operations"
              class="flex items-center gap-3 rounded-xl px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
              active-class="!bg-indigo-50 !text-indigo-700 ring-1 ring-inset ring-indigo-100 font-semibold"
            >
              <ChartBarSquareIcon class="h-5 w-5" /> Báo cáo
            </RouterLink>
          </div>
        </div>

        <!-- Người dùng -->
        <div>
          <p class="mb-2 px-4 text-xs font-bold text-slate-400 uppercase tracking-wider">Người dùng</p>
          <div class="space-y-1">
            <RouterLink
              to="/admin/customers"
              class="flex items-center gap-3 rounded-xl px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
              active-class="!bg-indigo-50 !text-indigo-700 ring-1 ring-inset ring-indigo-100 font-semibold"
            >
              <UsersIcon class="h-5 w-5" /> Khách hàng
            </RouterLink>
            <RouterLink
              to="/admin/sellers"
              class="flex items-center gap-3 rounded-xl px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
              active-class="!bg-indigo-50 !text-indigo-700 ring-1 ring-inset ring-indigo-100 font-semibold"
            >
              <BuildingStorefrontIcon class="h-5 w-5" /> Seller
            </RouterLink>
            <RouterLink
              to="/admin/seller-applications"
              class="flex items-center gap-3 rounded-xl px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
              active-class="!bg-indigo-50 !text-indigo-700 ring-1 ring-inset ring-indigo-100 font-semibold"
            >
              <CheckBadgeIcon class="h-5 w-5" /> Duyệt seller
            </RouterLink>
          </div>
        </div>
      </nav>

      <!-- Footer / Logout -->
      <div class="border-t border-slate-100 p-4 bg-slate-50">
        <button
          @click="logout"
          class="flex w-full items-center justify-center gap-2 rounded-xl bg-white border border-slate-200 px-4 py-2.5 text-sm font-bold text-slate-700 hover:border-rose-300 hover:bg-rose-50 hover:text-rose-600 transition-all shadow-sm"
        >
          <ArrowLeftStartOnRectangleIcon class="h-5 w-5" />
          Đăng xuất
        </button>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 overflow-y-auto bg-slate-50 p-6">
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
