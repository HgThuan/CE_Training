<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

import AuthPageShell from '../components/AuthPageShell.vue'
import FormMessage from '../components/FormMessage.vue'
import PasswordField from '../components/PasswordField.vue'
import { getErrorMessage } from '../errors'
import { homePathForRole } from '../routes'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()
const email = ref('')
const password = ref('')
const errorMessage = ref('')
const submitting = ref(false)
const submitted = ref(false)
const touched = reactive({ email: false, password: false })

const emailError = computed(() => {
  if (!email.value) return 'Vui lòng nhập email.'
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value)) return 'Email chưa đúng định dạng.'
  return ''
})
const passwordError = computed(() => (password.value ? '' : 'Vui lòng nhập mật khẩu.'))

async function submit(): Promise<void> {
  submitted.value = true
  errorMessage.value = ''
  if (emailError.value || passwordError.value || submitting.value) return
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
    description="Đăng nhập an toàn, thông tin của bạn luôn được bảo mật."
  >
    <form class="space-y-5" @submit.prevent="submit">
      <FormMessage v-if="errorMessage" :message="errorMessage" />
      <div>
        <label for="login-email" class="block text-sm font-medium text-gray-800">Email</label>
        <input
          id="login-email"
          v-model.trim="email"
          class="mt-2 w-full rounded-xl border px-4 py-3 text-base outline-none transition focus:ring-2"
          :class="
            (touched.email || submitted) && emailError
              ? 'border-red-500 focus:border-red-500 focus:ring-red-100'
              : 'border-gray-300 focus:border-indigo-500 focus:ring-indigo-100'
          "
          type="email"
          autocomplete="email"
          :aria-invalid="Boolean((touched.email || submitted) && emailError)"
          :aria-describedby="
            (touched.email || submitted) && emailError ? 'login-email-error' : undefined
          "
          required
          @blur="touched.email = true"
        />
        <p
          v-if="(touched.email || submitted) && emailError"
          id="login-email-error"
          class="mt-1.5 text-sm text-red-600"
          role="alert"
        >
          {{ emailError }}
        </p>
      </div>
      <PasswordField
        id="login-password"
        v-model="password"
        label="Mật khẩu"
        autocomplete="current-password"
        :error="touched.password || submitted ? passwordError : ''"
        @blur="touched.password = true"
      />
      <button
        class="w-full rounded-xl bg-indigo-600 px-4 py-3 font-semibold text-white hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
        type="submit"
        :disabled="submitting"
      >
        <span class="inline-flex items-center justify-center gap-2">
          <svg v-if="submitting" class="size-5 animate-spin" viewBox="0 0 24 24" aria-hidden="true">
            <circle
              class="opacity-25"
              cx="12"
              cy="12"
              r="9"
              fill="none"
              stroke="currentColor"
              stroke-width="3"
            />
            <path
              class="opacity-90"
              fill="currentColor"
              d="M21 12a9 9 0 0 0-9-9v3a6 6 0 0 1 6 6z"
            />
          </svg>
          {{ submitting ? 'Đang đăng nhập…' : 'Đăng nhập' }}
        </span>
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
    <div class="mt-5 border-t border-gray-200 pt-5 text-center text-sm text-gray-600">
      Chưa xác thực tài khoản?
      <RouterLink
        class="font-medium text-indigo-600 hover:text-indigo-500"
        to="/auth/resend-verification"
      >
        Gửi lại email
      </RouterLink>
    </div>
  </AuthPageShell>
</template>
