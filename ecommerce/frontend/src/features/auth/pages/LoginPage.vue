<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

import AuthPageShell from '../components/AuthPageShell.vue'
import FormMessage from '../components/FormMessage.vue'
import { getErrorMessage } from '../errors'
import { homePathForRole } from '../routes'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()
const email = ref('')
const password = ref('')
const errorMessage = ref('')
const submitting = ref(false)

async function submit(): Promise<void> {
  errorMessage.value = ''
  submitting.value = true
  try {
    await authStore.login({ email: email.value, password: password.value })
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : null
    const destination = redirect?.startsWith('/') ? redirect : homePathForRole(authStore.user!.role)
    await router.replace(destination)
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <AuthPageShell
    eyebrow="Tài khoản"
    title="Đăng nhập"
    description="Access token được giữ trong bộ nhớ; phiên dài hạn được bảo vệ bằng cookie HttpOnly."
  >
    <form class="space-y-5" @submit.prevent="submit">
      <FormMessage v-if="errorMessage" :message="errorMessage" />
      <label class="block text-sm font-medium text-gray-800">
        Email
        <input
          v-model.trim="email"
          class="mt-2 w-full rounded-xl border border-gray-300 px-4 py-3 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
          type="email"
          autocomplete="email"
          required
        />
      </label>
      <label class="block text-sm font-medium text-gray-800">
        Mật khẩu
        <input
          v-model="password"
          class="mt-2 w-full rounded-xl border border-gray-300 px-4 py-3 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
          type="password"
          autocomplete="current-password"
          required
        />
      </label>
      <button
        class="w-full rounded-xl bg-indigo-600 px-4 py-3 font-semibold text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
        type="submit"
        :disabled="submitting"
      >
        {{ submitting ? 'Đang đăng nhập…' : 'Đăng nhập' }}
      </button>
    </form>
    <div class="mt-6 flex justify-between text-sm">
      <RouterLink class="font-medium text-indigo-600 hover:text-indigo-500" to="/auth/register">
        Tạo tài khoản
      </RouterLink>
      <RouterLink
        class="font-medium text-indigo-600 hover:text-indigo-500"
        to="/auth/forgot-password"
      >
        Quên mật khẩu?
      </RouterLink>
    </div>
    <RouterLink
      class="mt-4 block text-center text-sm font-medium text-gray-600 hover:text-indigo-600"
      to="/auth/resend-verification"
    >
      Gửi lại email xác thực
    </RouterLink>
  </AuthPageShell>
</template>
