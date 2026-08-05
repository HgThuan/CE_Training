<script setup lang="ts">
import {
  ArrowLeftStartOnRectangleIcon,
  ArchiveBoxIcon,
  BuildingStorefrontIcon,
  ClipboardDocumentListIcon,
  CubeIcon,
  HomeIcon,
  ChatBubbleBottomCenterTextIcon,
  ArrowPathIcon,
  TicketIcon,
  UsersIcon,
  EnvelopeIcon,
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
    <aside
      class="w-[260px] flex-shrink-0 border-r border-slate-200 flex flex-col bg-white shadow-sm"
    >
      <!-- Header -->
      <div class="flex items-center gap-3 px-6 py-6 border-b border-slate-100">
        <span
          class="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 text-sm font-bold text-white shadow-md shadow-indigo-200"
        >
          M
        </span>
        <div>
          <span class="block font-black text-slate-800 text-lg tracking-tight leading-tight"
            >Seller Center</span
          >
          <span class="block text-xs font-semibold text-indigo-600 uppercase tracking-widest"
            >Mercato</span
          >
        </div>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 overflow-y-auto px-4 py-4 space-y-6 scrollbar-hide pb-8">
        <!-- Main -->
        <div>
          <RouterLink
            to="/seller"
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
          <p class="mb-2 px-4 text-xs font-bold text-slate-400 uppercase tracking-wider">
            Sản phẩm & Kho
          </p>
          <div class="space-y-1">
            <RouterLink
              to="/seller/products"
              class="flex items-center gap-3 rounded-xl px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
              active-class="!bg-indigo-50 !text-indigo-700 ring-1 ring-inset ring-indigo-100 font-semibold"
            >
              <CubeIcon class="h-5 w-5" /> Quản lý sản phẩm
            </RouterLink>
            <RouterLink
              to="/seller/inventory"
              class="flex items-center gap-3 rounded-xl px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
              active-class="!bg-indigo-50 !text-indigo-700 ring-1 ring-inset ring-indigo-100 font-semibold"
            >
              <ArchiveBoxIcon class="h-5 w-5" /> Tồn kho
            </RouterLink>
          </div>
        </div>

        <!-- Bán hàng -->
        <div>
          <p class="mb-2 px-4 text-xs font-bold text-slate-400 uppercase tracking-wider">
            Bán hàng
          </p>
          <div class="space-y-1">
            <RouterLink
              to="/seller/orders"
              class="flex items-center gap-3 rounded-xl px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
              active-class="!bg-indigo-50 !text-indigo-700 ring-1 ring-inset ring-indigo-100 font-semibold"
            >
              <ClipboardDocumentListIcon class="h-5 w-5" /> Đơn hàng
            </RouterLink>
            <RouterLink
              to="/seller/returns"
              class="flex items-center gap-3 rounded-xl px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
              active-class="!bg-indigo-50 !text-indigo-700 ring-1 ring-inset ring-indigo-100 font-semibold"
            >
              <ArrowPathIcon class="h-5 w-5" /> Trả hàng
            </RouterLink>
            <RouterLink
              to="/seller/promotions"
              class="flex items-center gap-3 rounded-xl px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
              active-class="!bg-indigo-50 !text-indigo-700 ring-1 ring-inset ring-indigo-100 font-semibold"
            >
              <TicketIcon class="h-5 w-5" /> Voucher
            </RouterLink>
          </div>
        </div>

        <!-- CSKH -->
        <div>
          <p class="mb-2 px-4 text-xs font-bold text-slate-400 uppercase tracking-wider">
            Khách hàng
          </p>
          <div class="space-y-1">
            <RouterLink
              to="/seller/chat"
              class="flex items-center gap-3 rounded-xl px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
              active-class="!bg-indigo-50 !text-indigo-700 ring-1 ring-inset ring-indigo-100 font-semibold"
            >
              <EnvelopeIcon class="h-5 w-5" /> Chat
            </RouterLink>
            <RouterLink
              to="/seller/customers"
              class="flex items-center gap-3 rounded-xl px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
              active-class="!bg-indigo-50 !text-indigo-700 ring-1 ring-inset ring-indigo-100 font-semibold"
            >
              <UsersIcon class="h-5 w-5" /> Khách hàng
            </RouterLink>
            <RouterLink
              to="/seller/reviews"
              class="flex items-center gap-3 rounded-xl px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
              active-class="!bg-indigo-50 !text-indigo-700 ring-1 ring-inset ring-indigo-100 font-semibold"
            >
              <ChatBubbleBottomCenterTextIcon class="h-5 w-5" /> Đánh giá
            </RouterLink>
          </div>
        </div>

        <!-- Cửa hàng -->
        <div>
          <p class="mb-2 px-4 text-xs font-bold text-slate-400 uppercase tracking-wider">
            Cửa hàng
          </p>
          <div class="space-y-1">
            <RouterLink
              to="/seller/shop"
              class="flex items-center gap-3 rounded-xl px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors"
              active-class="!bg-indigo-50 !text-indigo-700 ring-1 ring-inset ring-indigo-100 font-semibold"
            >
              <BuildingStorefrontIcon class="h-5 w-5" /> Hồ sơ gian hàng
            </RouterLink>
          </div>
        </div>
      </nav>

      <!-- Footer / Logout -->
      <div class="border-t border-slate-100 p-4 bg-slate-50">
        <button
          class="flex w-full items-center justify-center gap-2 rounded-xl bg-white border border-slate-200 px-4 py-2.5 text-sm font-bold text-slate-700 hover:border-rose-300 hover:bg-rose-50 hover:text-rose-600 transition-all shadow-sm"
          @click="logout"
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
