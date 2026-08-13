<script setup lang="ts">
import { computed, reactive, ref } from 'vue'

import { useAuthStore } from '@/stores/auth'

import AuthPageShell from '../components/AuthPageShell.vue'
import FormMessage from '../components/FormMessage.vue'
import PasswordField from '../components/PasswordField.vue'
import { getErrorMessage } from '../errors'

const authStore = useAuthStore()
const form = reactive({ full_name: '', email: '', password: '', password_confirm: '' })
const message = ref('')
const errorMessage = ref('')
const submitting = ref(false)
const resending = ref(false)
const registeredEmail = ref('')
const acceptedTerms = ref(false)
const submitted = ref(false)
const touched = reactive({ email: false, password: false, password_confirm: false, terms: false })

const emailError = computed(() => {
  if (!form.email) return 'Vui lòng nhập email.'
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) return 'Email chưa đúng định dạng.'
  return ''
})
const passwordChecks = computed(() => [
  { label: 'Cần nhập ít nhất 8 ký tự.', met: form.password.length >= 8 },
  {
    label: 'Cần thêm cả chữ hoa và chữ thường.',
    met: /[a-z]/.test(form.password) && /[A-Z]/.test(form.password),
  },
  { label: 'Cần thêm ít nhất một chữ số.', met: /\d/.test(form.password) },
  { label: 'Cần thêm ít nhất một ký tự đặc biệt.', met: /[^A-Za-z0-9]/.test(form.password) },
])
const unmetPasswordChecks = computed(() => passwordChecks.value.filter((check) => !check.met))
const passwordError = computed(() => {
  if (!form.password) return 'Vui lòng nhập mật khẩu.'
  return unmetPasswordChecks.value.length ? 'Mật khẩu còn thiếu một số thành phần.' : ''
})
const confirmError = computed(() => {
  if (!form.password_confirm) return 'Vui lòng nhập lại mật khẩu.'
  if (form.password_confirm !== form.password) return 'Mật khẩu xác nhận không khớp.'
  return ''
})
const termsError = computed(() =>
  acceptedTerms.value ? '' : 'Bạn cần đồng ý với điều khoản để đăng ký.',
)

async function submit(): Promise<void> {
  submitted.value = true
  message.value = ''
  errorMessage.value = ''
  registeredEmail.value = ''
  if (
    emailError.value ||
    passwordError.value ||
    confirmError.value ||
    termsError.value ||
    submitting.value
  )
    return
  submitting.value = true
  try {
    message.value = await authStore.register({ ...form })
    registeredEmail.value = form.email
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    submitting.value = false
  }
}

async function resendVerification(): Promise<void> {
  errorMessage.value = ''
  resending.value = true
  try {
    message.value = await authStore.resendVerification(registeredEmail.value)
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    resending.value = false
  }
}
</script>

<template>
  <AuthPageShell
    eyebrow="Tài khoản khách hàng"
    title="Tạo tài khoản"
    description="Mua sắm thuận tiện và quản lý đơn hàng của bạn ở một nơi."
  >
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
      <div>
        <label for="register-email" class="block text-sm font-medium text-gray-800">Email</label>
        <input
          id="register-email"
          v-model.trim="form.email"
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
            (touched.email || submitted) && emailError ? 'register-email-error' : undefined
          "
          required
          @blur="touched.email = true"
        />
        <p
          v-if="(touched.email || submitted) && emailError"
          id="register-email-error"
          class="mt-1.5 text-sm text-red-600"
          role="alert"
        >
          {{ emailError }}
        </p>
      </div>
      <PasswordField
        id="register-password"
        v-model="form.password"
        label="Mật khẩu"
        autocomplete="new-password"
        described-by="password-requirements"
        :error="touched.password || submitted ? passwordError : ''"
        @blur="touched.password = true"
      >
        <div
          v-if="form.password && unmetPasswordChecks.length"
          id="password-requirements"
          class="mt-3 space-y-1.5 text-sm text-red-600"
          aria-live="polite"
        >
          <p
            v-for="check in unmetPasswordChecks"
            :key="check.label"
            class="flex items-center gap-2"
          >
            <span class="size-1.5 shrink-0 rounded-full bg-red-500" aria-hidden="true" />
            {{ check.label }}
          </p>
        </div>
      </PasswordField>
      <PasswordField
        id="register-password-confirm"
        v-model="form.password_confirm"
        label="Xác nhận mật khẩu"
        autocomplete="new-password"
        :error="touched.password_confirm || submitted ? confirmError : ''"
        @blur="touched.password_confirm = true"
      />
      <div>
        <label class="flex cursor-pointer items-start gap-3 text-sm leading-6 text-gray-700">
          <input
            v-model="acceptedTerms"
            class="mt-1 size-4 shrink-0 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            type="checkbox"
            :aria-invalid="Boolean((touched.terms || submitted) && termsError)"
            aria-describedby="terms-error"
            required
            @blur="touched.terms = true"
          />
          <span>
            Tôi đồng ý với
            <RouterLink class="font-medium text-indigo-600 hover:text-indigo-500" to="/terms"
              >Điều khoản sử dụng</RouterLink
            >
            và
            <RouterLink class="font-medium text-indigo-600 hover:text-indigo-500" to="/privacy"
              >Chính sách bảo mật</RouterLink
            >.
          </span>
        </label>
        <p
          v-if="(touched.terms || submitted) && termsError"
          id="terms-error"
          class="mt-1.5 text-sm text-red-600"
          role="alert"
        >
          {{ termsError }}
        </p>
      </div>
      <button
        class="w-full rounded-xl bg-indigo-600 px-4 py-3 font-semibold text-white disabled:opacity-60"
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
          {{ submitting ? 'Đang tạo tài khoản…' : 'Đăng ký' }}
        </span>
      </button>
      <button
        v-if="registeredEmail"
        class="w-full rounded-xl border border-indigo-200 px-4 py-3 font-semibold text-indigo-700 disabled:opacity-60"
        type="button"
        :disabled="resending"
        @click="resendVerification"
      >
        {{ resending ? 'Đang gửi lại…' : 'Không nhận được email? Gửi lại xác thực' }}
      </button>
    </form>
    <RouterLink class="mt-6 block text-center text-sm font-medium text-indigo-600" to="/auth/login">
      Đã có tài khoản? Đăng nhập
    </RouterLink>
    <p class="mt-4 text-center text-sm leading-6 text-gray-600">
      Bạn muốn bán hàng? Hãy tạo tài khoản khách hàng, sau đó đăng ký hồ sơ nhà bán hàng trong trang
      cá nhân.
    </p>
  </AuthPageShell>
</template>
