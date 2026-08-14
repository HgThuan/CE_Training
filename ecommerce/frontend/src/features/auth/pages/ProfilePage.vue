<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

import { cropAvatarToSquare } from '../avatar'
import FormMessage from '../components/FormMessage.vue'
import { getErrorMessage } from '../errors'

const authStore = useAuthStore()
const router = useRouter()
const profileForm = reactive({
  full_name: authStore.user?.full_name ?? '',
  phone: authStore.user?.phone ?? '',
  date_of_birth: authStore.user?.date_of_birth ?? '',
  gender: authStore.user?.gender ?? '',
})
const passwordForm = reactive({
  old_password: '',
  new_password: '',
  new_password_confirm: '',
})
const profileMessage = ref('')
const passwordMessage = ref('')
const errorMessage = ref('')
const avatarPreview = ref(authStore.user?.avatar_url ?? '')
const croppedAvatar = ref<Blob | null>(null)
const avatarSaving = ref(false)
const avatarInput = ref<HTMLInputElement | null>(null)

async function selectAvatar(event: Event): Promise<void> {
  errorMessage.value = ''
  profileMessage.value = ''
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  try {
    const blob = await cropAvatarToSquare(file)
    croppedAvatar.value = blob
    if (avatarPreview.value.startsWith('blob:')) URL.revokeObjectURL(avatarPreview.value)
    avatarPreview.value = URL.createObjectURL(blob)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Không thể xử lý ảnh đã chọn'
    input.value = ''
  }
}

async function saveAvatar(): Promise<void> {
  if (!croppedAvatar.value) return
  avatarSaving.value = true
  errorMessage.value = ''
  try {
    profileMessage.value = await authStore.uploadAvatar(croppedAvatar.value)
    if (avatarPreview.value.startsWith('blob:')) URL.revokeObjectURL(avatarPreview.value)
    avatarPreview.value = authStore.user?.avatar_url ?? ''
    croppedAvatar.value = null
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    avatarSaving.value = false
  }
}

async function saveProfile(): Promise<void> {
  errorMessage.value = ''
  profileMessage.value = ''
  try {
    profileMessage.value = await authStore.updateProfile({
      ...profileForm,
      date_of_birth: profileForm.date_of_birth || null,
    })
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
}

async function changePassword(): Promise<void> {
  errorMessage.value = ''
  passwordMessage.value = ''
  try {
    passwordMessage.value = await authStore.changePassword({ ...passwordForm })
    await router.replace('/auth/login')
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
}

async function logout(): Promise<void> {
  await authStore.logout()
  await router.replace('/auth/login')
}
</script>

<template>
  <main class="mx-auto max-w-4xl px-5 py-10">
    <header class="flex flex-wrap items-center justify-between gap-4">
      <div>
        <h1 class="text-3xl font-bold text-[#0b2a25]">Hồ sơ cá nhân</h1>
        <p class="mt-1 text-gray-600">{{ authStore.user?.email }}</p>
      </div>
      <button class="rounded-xl border border-gray-300 px-4 py-2 font-semibold" @click="logout">
        Đăng xuất
      </button>
    </header>

    <FormMessage v-if="errorMessage" class="mt-6" :message="errorMessage" />

    <div class="mt-8 grid gap-6 lg:grid-cols-2">
      <form class="market-panel space-y-4 p-6" @submit.prevent="saveProfile">
        <h2 class="text-xl font-bold">Thông tin chung</h2>
        <FormMessage v-if="profileMessage" :message="profileMessage" variant="success" />
        <section class="flex flex-wrap items-center gap-4 rounded-xl bg-gray-50 p-4">
          <img
            v-if="avatarPreview"
            :src="avatarPreview"
            alt="Ảnh đại diện"
            class="size-20 rounded-full object-cover ring-2 ring-white"
          />
          <div
            v-else
            class="grid size-20 place-items-center rounded-full bg-[#e8eee9] text-2xl font-bold text-[#173b35]"
            aria-label="Chưa có ảnh đại diện"
          >
            {{ authStore.user?.full_name?.charAt(0).toUpperCase() || '?' }}
          </div>
          <div class="min-w-0 flex-1 space-y-2">
            <div class="block text-sm font-semibold">
              Ảnh đại diện
              <input
                ref="avatarInput"
                class="sr-only"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                @change="selectAvatar"
              />
              <button
                class="mt-2 rounded-xl border border-[#173b35]/25 bg-white px-4 py-2.5 text-sm font-bold text-[#173b35] hover:border-[#e85d3f]"
                type="button"
                @click="avatarInput?.click()"
              >
                Chọn ảnh từ thiết bị
              </button>
            </div>
            <button
              v-if="croppedAvatar"
              class="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
              :disabled="avatarSaving"
              type="button"
              @click="saveAvatar"
            >
              {{ avatarSaving ? 'Đang tải lên…' : 'Lưu ảnh đại diện' }}
            </button>
            <p class="text-xs text-gray-500">JPEG, PNG hoặc WebP; tối đa 5 MB.</p>
          </div>
        </section>
        <label class="block text-sm font-medium">
          Họ tên
          <input
            v-model.trim="profileForm.full_name"
            class="mt-2 w-full rounded-xl border px-3 py-2"
          />
        </label>
        <label class="block text-sm font-medium">
          Điện thoại
          <input v-model.trim="profileForm.phone" class="mt-2 w-full rounded-xl border px-3 py-2" />
        </label>
        <label class="block text-sm font-medium">
          Ngày sinh
          <input
            v-model="profileForm.date_of_birth"
            class="mt-2 w-full rounded-xl border px-3 py-2"
            type="date"
          />
        </label>
        <label class="block text-sm font-medium">
          Giới tính
          <select v-model="profileForm.gender" class="mt-2 w-full rounded-xl border px-3 py-2">
            <option value="">Không cung cấp</option>
            <option value="male">Nam</option>
            <option value="female">Nữ</option>
            <option value="other">Khác</option>
          </select>
        </label>
        <button class="rounded-xl bg-indigo-600 px-4 py-2 font-semibold text-white" type="submit">
          Lưu hồ sơ
        </button>
      </form>

      <form class="market-panel space-y-4 p-6" @submit.prevent="changePassword">
        <h2 class="text-xl font-bold">Đổi mật khẩu</h2>
        <FormMessage v-if="passwordMessage" :message="passwordMessage" variant="success" />
        <label class="block text-sm font-medium">
          Mật khẩu hiện tại
          <input
            v-model="passwordForm.old_password"
            class="mt-2 w-full rounded-xl border px-3 py-2"
            type="password"
            autocomplete="current-password"
            required
          />
        </label>
        <label class="block text-sm font-medium">
          Mật khẩu mới
          <input
            v-model="passwordForm.new_password"
            class="mt-2 w-full rounded-xl border px-3 py-2"
            type="password"
            autocomplete="new-password"
            minlength="8"
            required
          />
        </label>
        <label class="block text-sm font-medium">
          Xác nhận mật khẩu mới
          <input
            v-model="passwordForm.new_password_confirm"
            class="mt-2 w-full rounded-xl border px-3 py-2"
            type="password"
            autocomplete="new-password"
            required
          />
        </label>
        <button class="rounded-xl bg-gray-950 px-4 py-2 font-semibold text-white" type="submit">
          Đổi mật khẩu
        </button>
      </form>
    </div>

    <RouterLink
      v-if="authStore.user?.role === 'customer'"
      class="mt-6 flex items-center justify-between rounded-2xl bg-indigo-50 p-5 font-semibold text-indigo-800 ring-1 ring-indigo-100"
      to="/account/addresses"
    >
      <span>Quản lý sổ địa chỉ nhận hàng</span>
      <span aria-hidden="true">→</span>
    </RouterLink>
    <RouterLink
      v-if="authStore.user?.role === 'customer'"
      class="mt-4 flex items-center justify-between rounded-2xl bg-emerald-50 p-5 font-semibold text-emerald-900 ring-1 ring-emerald-100"
      to="/account/seller-application"
    >
      <span>Đăng ký trở thành nhà bán hàng</span>
      <span aria-hidden="true">→</span>
    </RouterLink>
  </main>
</template>
