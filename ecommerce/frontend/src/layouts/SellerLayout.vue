<script setup lang="ts">
import {
  ArrowLeftStartOnRectangleIcon,
  BuildingStorefrontIcon,
  CubeIcon,
  HomeIcon,
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
  <div class="min-h-screen bg-slate-50">
    <header class="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div class="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
        <RouterLink class="flex items-center gap-3" to="/seller">
          <span
            class="grid h-10 w-10 place-items-center rounded-2xl bg-indigo-600 font-black text-white"
            >M</span
          >
          <div class="hidden sm:block">
            <p class="text-xs font-bold uppercase tracking-widest text-indigo-600">Mercato</p>
            <p class="text-sm font-black">Seller Center</p>
          </div>
        </RouterLink>
        <nav class="flex items-center gap-1 text-sm font-bold" aria-label="Seller navigation">
          <RouterLink
            class="inline-flex items-center gap-2 rounded-xl px-3 py-2 text-slate-600 hover:bg-slate-100 hover:text-slate-950"
            active-class="!bg-indigo-50 !text-indigo-700"
            to="/seller"
          >
            <HomeIcon class="h-4 w-4" />
            <span class="hidden md:inline">Tổng quan</span>
          </RouterLink>
          <RouterLink
            class="inline-flex items-center gap-2 rounded-xl px-3 py-2 text-slate-600 hover:bg-slate-100 hover:text-slate-950"
            active-class="!bg-indigo-50 !text-indigo-700"
            to="/seller/products"
          >
            <CubeIcon class="h-4 w-4" />
            <span class="hidden md:inline">Sản phẩm</span>
          </RouterLink>
          <RouterLink
            class="inline-flex items-center gap-2 rounded-xl px-3 py-2 text-slate-600 hover:bg-slate-100 hover:text-slate-950"
            active-class="!bg-indigo-50 !text-indigo-700"
            to="/seller/shop"
          >
            <BuildingStorefrontIcon class="h-4 w-4" />
            <span class="hidden md:inline">Gian hàng</span>
          </RouterLink>
          <button
            class="ml-1 grid h-10 w-10 place-items-center rounded-xl text-slate-500 hover:bg-rose-50 hover:text-rose-700"
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
