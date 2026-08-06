<script setup lang="ts">
import { SparklesIcon } from '@heroicons/vue/24/outline'

import { homePathForRole } from '@/features/auth/routes'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
</script>

<template>
  <main class="flex min-h-screen items-center justify-center bg-slate-950 px-6 py-16 text-white">
    <section
      class="w-full max-w-5xl overflow-hidden rounded-[2rem] bg-white p-8 text-slate-950 shadow-2xl sm:p-12"
    >
      <div class="mb-6 flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50">
        <SparklesIcon class="h-7 w-7 text-indigo-600" aria-hidden="true" />
      </div>
      <p class="text-sm font-semibold uppercase tracking-widest text-indigo-600">
        Mercato marketplace
      </p>
      <h1 class="mt-3 max-w-3xl text-4xl font-black tracking-tight text-gray-950 sm:text-6xl">
        Multi-Vendor AI E-commerce
      </h1>
      <p class="mt-5 max-w-2xl text-base leading-7 text-gray-600 sm:text-lg">
        Khám phá catalog đã kiểm duyệt, lựa chọn đúng biến thể và mua sắm từ nhiều gian hàng trong
        một trải nghiệm liền mạch.
      </p>
      <div class="mt-8 flex flex-wrap gap-3">
        <RouterLink
          class="rounded-xl bg-indigo-600 px-5 py-3 font-semibold text-white"
          to="/products"
        >
          Khám phá sản phẩm
        </RouterLink>
        <RouterLink
          v-if="authStore.user"
          :to="homePathForRole(authStore.user.role)"
          class="inline-flex rounded-xl border border-slate-300 px-5 py-3 font-semibold"
        >
          Mở workspace
        </RouterLink>
        <template v-else>
          <RouterLink
            class="rounded-xl border border-slate-300 px-5 py-3 font-semibold"
            to="/auth/login"
          >
            Đăng nhập
          </RouterLink>
          <RouterLink
            class="rounded-xl border border-gray-300 px-5 py-3 font-semibold"
            to="/auth/register"
          >
            Đăng ký
          </RouterLink>
        </template>
      </div>
    </section>
  </main>
</template>
