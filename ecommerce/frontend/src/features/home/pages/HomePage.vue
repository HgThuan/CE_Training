<script setup lang="ts">
import { SparklesIcon } from '@heroicons/vue/24/outline'

import { homePathForRole } from '@/features/auth/routes'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
</script>

<template>
  <main class="flex min-h-screen items-center justify-center px-6 py-16">
    <section class="w-full max-w-3xl rounded-3xl bg-white p-8 shadow-sm ring-1 ring-gray-200">
      <div class="mb-6 flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50">
        <SparklesIcon class="h-7 w-7 text-indigo-600" aria-hidden="true" />
      </div>
      <p class="text-sm font-semibold uppercase tracking-widest text-indigo-600">Auth foundation</p>
      <h1 class="mt-3 text-3xl font-bold tracking-tight text-gray-950 sm:text-5xl">
        Multi-Vendor AI E-commerce
      </h1>
      <p class="mt-5 max-w-2xl text-base leading-7 text-gray-600 sm:text-lg">
        Đăng ký, xác thực email, JWT rotation, khôi phục mật khẩu và phân quyền ba vai trò đã được
        kết nối từ Vue tới Django.
      </p>
      <div class="mt-8 flex flex-wrap gap-3">
        <RouterLink
          v-if="authStore.user"
          :to="homePathForRole(authStore.user.role)"
          class="inline-flex rounded-xl bg-indigo-600 px-5 py-3 font-semibold text-white"
        >
          Mở workspace
        </RouterLink>
        <template v-else>
          <RouterLink
            class="rounded-xl bg-indigo-600 px-5 py-3 font-semibold text-white"
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
