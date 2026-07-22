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

async function submit(): Promise<void> {
  message.value = ''
  errorMessage.value = ''
  try {
    message.value = await authStore.resendVerification(email.value)
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
}
</script>

<template>
  <AuthPageShell eyebrow="Xác thực" title="Gửi lại email xác thực">
    <form class="space-y-5" @submit.prevent="submit">
      <FormMessage v-if="message" :message="message" variant="success" />
      <FormMessage v-if="errorMessage" :message="errorMessage" />
      <label class="block text-sm font-medium">
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
        class="w-full rounded-xl bg-indigo-600 px-4 py-3 font-semibold text-white"
        type="submit"
      >
        Gửi lại email
      </button>
    </form>
  </AuthPageShell>
</template>
