<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

import AuthPageShell from '../components/AuthPageShell.vue'
import FormMessage from '../components/FormMessage.vue'
import { getErrorMessage } from '../errors'

const authStore = useAuthStore()
const route = useRoute()
const message = ref('Đang xác thực email…')
const failed = ref(false)

onMounted(async () => {
  const token = typeof route.query.token === 'string' ? route.query.token : ''
  if (!token) {
    message.value = 'Liên kết xác thực không có token'
    failed.value = true
    return
  }
  try {
    message.value = await authStore.verifyEmail(token)
  } catch (error) {
    message.value = getErrorMessage(error)
    failed.value = true
  }
})
</script>

<template>
  <AuthPageShell eyebrow="Xác thực" title="Xác thực email">
    <FormMessage :message="message" :variant="failed ? 'error' : 'success'" />
    <RouterLink
      class="mt-6 block text-center text-sm font-semibold text-indigo-600"
      to="/auth/login"
    >
      Đi tới đăng nhập
    </RouterLink>
  </AuthPageShell>
</template>
