<script setup lang="ts">
import { reactive, ref } from 'vue'

import { useAuthStore } from '@/stores/auth'

import AuthPageShell from '../components/AuthPageShell.vue'
import FormMessage from '../components/FormMessage.vue'
import { getErrorMessage } from '../errors'

const authStore = useAuthStore()
const form = reactive({ full_name: '', email: '', password: '', password_confirm: '' })
const message = ref('')
const errorMessage = ref('')
const submitting = ref(false)

async function submit(): Promise<void> {
  message.value = ''
  errorMessage.value = ''
  submitting.value = true
  try {
    message.value = await authStore.register({ ...form })
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <AuthPageShell eyebrow="Khách hàng" title="Tạo tài khoản">
    <form class="space-y-4" @submit.prevent="submit">
      <FormMessage v-if="message" :message="message" variant="success" />
      <FormMessage v-if="errorMessage" :message="errorMessage" />
      <label class="block text-sm font-medium text-gray-800">
        Họ và tên
        <input
          v-model.trim="form.full_name"
          class="mt-2 w-full rounded-xl border border-gray-300 px-4 py-3"
          autocomplete="name"
        />
      </label>
      <label class="block text-sm font-medium text-gray-800">
        Email
        <input
          v-model.trim="form.email"
          class="mt-2 w-full rounded-xl border border-gray-300 px-4 py-3"
          type="email"
          autocomplete="email"
          required
        />
      </label>
      <label class="block text-sm font-medium text-gray-800">
        Mật khẩu
        <input
          v-model="form.password"
          class="mt-2 w-full rounded-xl border border-gray-300 px-4 py-3"
          type="password"
          autocomplete="new-password"
          minlength="8"
          required
        />
      </label>
      <label class="block text-sm font-medium text-gray-800">
        Xác nhận mật khẩu
        <input
          v-model="form.password_confirm"
          class="mt-2 w-full rounded-xl border border-gray-300 px-4 py-3"
          type="password"
          autocomplete="new-password"
          required
        />
      </label>
      <button
        class="w-full rounded-xl bg-indigo-600 px-4 py-3 font-semibold text-white disabled:opacity-60"
        type="submit"
        :disabled="submitting"
      >
        {{ submitting ? 'Đang tạo…' : 'Đăng ký' }}
      </button>
    </form>
    <RouterLink class="mt-6 block text-center text-sm font-medium text-indigo-600" to="/auth/login">
      Đã có tài khoản? Đăng nhập
    </RouterLink>
  </AuthPageShell>
</template>
