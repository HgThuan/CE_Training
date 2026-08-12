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
  UserIcon,
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
  <div class="flex min-h-screen bg-slate-50 text-slate-900 font-sans selection:bg-indigo-500/30">
    <!-- Premium Dark Sidebar -->
    <aside
      class="w-[280px] flex-shrink-0 flex flex-col bg-slate-950 text-slate-300 shadow-2xl relative z-10"
    >
      <!-- Glassy Header -->
      <div class="sticky top-0 z-20 flex items-center gap-4 px-6 py-8 bg-slate-950/80 backdrop-blur-xl border-b border-white/5">
        <div
          class="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 text-lg font-black text-white shadow-lg shadow-indigo-500/30 ring-1 ring-white/10"
        >
          M
        </div>
        <div>
          <span class="block font-black text-white text-xl tracking-tight leading-tight"
            >Seller Center</span
          >
          <span class="block text-[11px] font-bold text-indigo-400 uppercase tracking-[0.2em]"
            >Mercato Pro</span
          >
        </div>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 overflow-y-auto px-4 py-6 space-y-8 scrollbar-hide pb-8">
        <!-- Main -->
        <div>
          <RouterLink
            to="/seller"
            end
            class="group flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-semibold transition-all duration-300 hover:bg-white/5 hover:text-white"
            active-class="!bg-indigo-600 !text-white shadow-lg shadow-indigo-500/25 ring-1 ring-indigo-400/30"
          >
            <HomeIcon class="h-5 w-5 transition-transform group-hover:scale-110" stroke-width="2" />
            Tổng quan
          </RouterLink>
        </div>

        <!-- Sản phẩm & Kho -->
        <div>
          <p class="mb-3 px-4 text-[11px] font-black text-slate-500 uppercase tracking-widest">
            Sản phẩm & Kho
          </p>
          <div class="space-y-1">
            <RouterLink
              to="/seller/products"
              class="group flex items-center gap-3 rounded-2xl px-4 py-2.5 text-sm font-medium transition-all duration-300 hover:bg-white/5 hover:text-white hover:translate-x-1"
              active-class="!bg-indigo-600/10 !text-indigo-400 font-bold"
            >
              <CubeIcon class="h-5 w-5" stroke-width="2" /> Quản lý sản phẩm
            </RouterLink>
            <RouterLink
              to="/seller/inventory"
              class="group flex items-center gap-3 rounded-2xl px-4 py-2.5 text-sm font-medium transition-all duration-300 hover:bg-white/5 hover:text-white hover:translate-x-1"
              active-class="!bg-indigo-600/10 !text-indigo-400 font-bold"
            >
              <ArchiveBoxIcon class="h-5 w-5" stroke-width="2" /> Tồn kho
            </RouterLink>
          </div>
        </div>

        <!-- Bán hàng -->
        <div>
          <p class="mb-3 px-4 text-[11px] font-black text-slate-500 uppercase tracking-widest">
            Bán hàng
          </p>
          <div class="space-y-1">
            <RouterLink
              to="/seller/orders"
              class="group flex items-center gap-3 rounded-2xl px-4 py-2.5 text-sm font-medium transition-all duration-300 hover:bg-white/5 hover:text-white hover:translate-x-1"
              active-class="!bg-indigo-600/10 !text-indigo-400 font-bold"
            >
              <ClipboardDocumentListIcon class="h-5 w-5" stroke-width="2" /> Đơn hàng
            </RouterLink>
            <RouterLink
              to="/seller/returns"
              class="group flex items-center gap-3 rounded-2xl px-4 py-2.5 text-sm font-medium transition-all duration-300 hover:bg-white/5 hover:text-white hover:translate-x-1"
              active-class="!bg-indigo-600/10 !text-indigo-400 font-bold"
            >
              <ArrowPathIcon class="h-5 w-5" stroke-width="2" /> Trả hàng
            </RouterLink>
            <RouterLink
              to="/seller/promotions"
              class="group flex items-center gap-3 rounded-2xl px-4 py-2.5 text-sm font-medium transition-all duration-300 hover:bg-white/5 hover:text-white hover:translate-x-1"
              active-class="!bg-indigo-600/10 !text-indigo-400 font-bold"
            >
              <TicketIcon class="h-5 w-5" stroke-width="2" /> Khuyến mãi
            </RouterLink>
          </div>
        </div>

        <!-- CSKH -->
        <div>
          <p class="mb-3 px-4 text-[11px] font-black text-slate-500 uppercase tracking-widest">
            Khách hàng
          </p>
          <div class="space-y-1">
            <RouterLink
              to="/seller/chat"
              class="group flex items-center gap-3 rounded-2xl px-4 py-2.5 text-sm font-medium transition-all duration-300 hover:bg-white/5 hover:text-white hover:translate-x-1"
              active-class="!bg-indigo-600/10 !text-indigo-400 font-bold"
            >
              <EnvelopeIcon class="h-5 w-5" stroke-width="2" /> Chat
            </RouterLink>
            <RouterLink
              to="/seller/customers"
              class="group flex items-center gap-3 rounded-2xl px-4 py-2.5 text-sm font-medium transition-all duration-300 hover:bg-white/5 hover:text-white hover:translate-x-1"
              active-class="!bg-indigo-600/10 !text-indigo-400 font-bold"
            >
              <UsersIcon class="h-5 w-5" stroke-width="2" /> Khách hàng
            </RouterLink>
            <RouterLink
              to="/seller/reviews"
              class="group flex items-center gap-3 rounded-2xl px-4 py-2.5 text-sm font-medium transition-all duration-300 hover:bg-white/5 hover:text-white hover:translate-x-1"
              active-class="!bg-indigo-600/10 !text-indigo-400 font-bold"
            >
              <ChatBubbleBottomCenterTextIcon class="h-5 w-5" stroke-width="2" /> Đánh giá
            </RouterLink>
          </div>
        </div>

        <!-- Cửa hàng & Cá nhân -->
        <div>
          <p class="mb-3 px-4 text-[11px] font-black text-slate-500 uppercase tracking-widest">
            Cửa hàng & Cá nhân
          </p>
          <div class="space-y-1">
            <RouterLink
              to="/seller/shop"
              class="group flex items-center gap-3 rounded-2xl px-4 py-2.5 text-sm font-medium transition-all duration-300 hover:bg-white/5 hover:text-white hover:translate-x-1"
              active-class="!bg-indigo-600/10 !text-indigo-400 font-bold"
            >
              <BuildingStorefrontIcon class="h-5 w-5" stroke-width="2" /> Hồ sơ gian hàng
            </RouterLink>
            <RouterLink
              to="/account/profile"
              class="group flex items-center gap-3 rounded-2xl px-4 py-2.5 text-sm font-medium transition-all duration-300 hover:bg-white/5 hover:text-white hover:translate-x-1"
              active-class="!bg-indigo-600/10 !text-indigo-400 font-bold"
            >
              <UserIcon class="h-5 w-5" stroke-width="2" /> Hồ sơ cá nhân
            </RouterLink>
          </div>
        </div>
      </nav>

      <!-- Footer / Logout -->
      <div class="p-4 bg-slate-900/50 border-t border-white/5 mt-auto">
        <button
          class="group flex w-full items-center justify-center gap-2 rounded-2xl bg-white/5 px-4 py-3 text-sm font-bold text-slate-300 transition-all duration-300 hover:bg-rose-500/10 hover:text-rose-400 ring-1 ring-transparent hover:ring-rose-500/30"
          @click="logout"
        >
          <ArrowLeftStartOnRectangleIcon class="h-5 w-5 transition-transform group-hover:-translate-x-1" stroke-width="2" />
          Đăng xuất
        </button>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 overflow-y-auto bg-slate-50">
      <div class="min-h-full p-8 max-w-[1600px] mx-auto">
        <RouterView />
      </div>
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
