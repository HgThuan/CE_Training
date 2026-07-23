<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

import AuthPageShell from '../components/AuthPageShell.vue'
import FormMessage from '../components/FormMessage.vue'
import { getErrorMessage } from '../errors'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()
const form = reactive({ new_password: '', new_password_confirm: '' })
const errorMessage = ref('')
const submitting = ref(false)

async function submit(): Promise<void> {
  const uid = typeof route.query.uid === 'string' ? route.query.uid : ''
  const token = typeof route.query.token === 'string' ? route.query.token : ''
  if (!uid || !token) {
    errorMessage.value = 'Liên kết đặt lại mật khẩu không đầy đủ'
    return
  }
  submitting.value = true
  errorMessage.value = ''
  try {
    await authStore.resetPassword({ uid, token, ...form })
    await router.replace({ path: '/auth/login', query: { password_reset: 'success' } })
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <AuthPageShell eyebrow="Khôi phục" title="Đặt mật khẩu mới">
    <form class="space-y-5" @submit.prevent="submit">
      <FormMessage v-if="errorMessage" :message="errorMessage" />
      <label class="block text-sm font-medium text-gray-800">
        Mật khẩu mới
        <input
          v-model="form.new_password"
          class="mt-2 w-full rounded-xl border border-gray-300 px-4 py-3"
          type="password"
          autocomplete="new-password"
          minlength="8"
          required
        />
      </label>
      <label class="block text-sm font-medium text-gray-800">
        Xác nhận mật khẩu mới
        <input
          v-model="form.new_password_confirm"
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
        {{ submitting ? 'Đang cập nhật…' : 'Đặt lại mật khẩu' }}
      </button>
    </form>
  </AuthPageShell>
</template>
