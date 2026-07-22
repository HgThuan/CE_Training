<script setup lang="ts">
import { ref } from 'vue'

import { useAuthStore } from '@/stores/auth'

import AuthPageShell from '../components/AuthPageShell.vue'
import FormMessage from '../components/FormMessage.vue'
import { getErrorMessage } from '../errors'

const authStore = useAuthStore()
const email = ref('')
const message = ref('')
const errorMessage = ref('')
const submitting = ref(false)

async function submit(): Promise<void> {
  message.value = ''
  errorMessage.value = ''
  submitting.value = true
  try {
    message.value = await authStore.forgotPassword(email.value)
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <AuthPageShell
    eyebrow="Khôi phục"
    title="Quên mật khẩu"
    description="Phản hồi không tiết lộ email có tồn tại trong hệ thống hay không."
  >
    <form class="space-y-5" @submit.prevent="submit">
      <FormMessage v-if="message" :message="message" variant="success" />
      <FormMessage v-if="errorMessage" :message="errorMessage" />
      <label class="block text-sm font-medium text-gray-800">
        Email
        <input
          v-model.trim="email"
          class="mt-2 w-full rounded-xl border border-gray-300 px-4 py-3"
          type="email"
          autocomplete="email"
          required
        />
      </label>
      <button
        class="w-full rounded-xl bg-indigo-600 px-4 py-3 font-semibold text-white disabled:opacity-60"
        type="submit"
        :disabled="submitting"
      >
        {{ submitting ? 'Đang gửi…' : 'Gửi hướng dẫn' }}
      </button>
    </form>
    <RouterLink class="mt-6 block text-center text-sm font-medium text-indigo-600" to="/auth/login">
      Quay lại đăng nhập
    </RouterLink>
  </AuthPageShell>
</template>
