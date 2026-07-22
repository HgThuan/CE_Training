<script setup lang="ts">
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()

async function logout(): Promise<void> {
  await authStore.logout()
  await router.replace('/auth/login')
}
</script>

<template>
  <main class="mx-auto max-w-5xl px-6 py-12">
    <section class="rounded-3xl bg-white p-8 shadow-sm ring-1 ring-gray-200">
      <p class="text-sm font-bold uppercase tracking-[0.2em] text-indigo-600">
        {{ authStore.user?.role }} workspace
      </p>
      <h1 class="mt-3 text-4xl font-bold text-gray-950">
        Xin chào, {{ authStore.user?.full_name || authStore.user?.email }}
      </h1>
      <p class="mt-4 text-gray-600">
        Route này đã được bảo vệ theo vai trò. Các dashboard nghiệp vụ sẽ được triển khai ở bước
        sau.
      </p>
      <div class="mt-8 flex flex-wrap gap-3">
        <RouterLink
          class="rounded-xl bg-indigo-600 px-4 py-2 font-semibold text-white"
          to="/account/profile"
        >
          Hồ sơ cá nhân
        </RouterLink>
        <RouterLink
          v-if="authStore.user?.role === 'admin'"
          class="rounded-xl border border-gray-300 px-4 py-2 font-semibold"
          to="/admin/roles"
        >
          Phân quyền
        </RouterLink>
        <RouterLink
          v-if="authStore.user?.role === 'admin'"
          class="rounded-xl border border-gray-300 px-4 py-2 font-semibold"
          to="/admin/customers"
        >
          Quản lý khách hàng
        </RouterLink>
        <button class="rounded-xl border border-gray-300 px-4 py-2 font-semibold" @click="logout">
          Đăng xuất
        </button>
      </div>
    </section>
  </main>
</template>
