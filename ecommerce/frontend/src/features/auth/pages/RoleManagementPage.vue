<script setup lang="ts">
import { ref } from 'vue'

import { authApi } from '../api'
import FormMessage from '../components/FormMessage.vue'
import { getErrorMessage } from '../errors'
import type { AuthenticatedUser, UserRole } from '../types'

const userId = ref<number | null>(null)
const role = ref<UserRole>('customer')
const updatedUser = ref<AuthenticatedUser | null>(null)
const message = ref('')
const errorMessage = ref('')

async function assignRole(): Promise<void> {
  if (!userId.value) return
  message.value = ''
  errorMessage.value = ''
  try {
    const response = await authApi.assignRole(userId.value, role.value)
    updatedUser.value = response.data.data
    message.value = response.data.message
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
}
</script>

<template>
  <main class="mx-auto max-w-3xl px-6 py-12">
    <RouterLink class="font-semibold text-indigo-600" to="/admin">← Admin workspace</RouterLink>
    <section class="mt-6 rounded-3xl bg-white p-8 ring-1 ring-gray-200">
      <p class="text-sm font-bold uppercase tracking-widest text-indigo-600">ADM-08</p>
      <h1 class="mt-2 text-3xl font-bold">Gán vai trò chính</h1>
      <p class="mt-3 text-sm leading-6 text-gray-600">
        Hành động được kiểm tra ở API, vô hiệu toàn bộ phiên cũ và ghi Audit Log.
      </p>
      <form class="mt-8 space-y-5" @submit.prevent="assignRole">
        <FormMessage v-if="message" :message="message" variant="success" />
        <FormMessage v-if="errorMessage" :message="errorMessage" />
        <label class="block text-sm font-medium">
          User ID
          <input
            v-model="userId"
            class="mt-2 w-full rounded-xl border px-4 py-3"
            type="number"
            min="1"
            required
          />
        </label>
        <label class="block text-sm font-medium">
          Vai trò
          <select v-model="role" class="mt-2 w-full rounded-xl border px-4 py-3">
            <option value="customer">Customer</option>
            <option value="seller">Seller</option>
            <option value="admin">Admin</option>
          </select>
        </label>
        <button class="rounded-xl bg-indigo-600 px-5 py-3 font-semibold text-white" type="submit">
          Cập nhật vai trò
        </button>
      </form>
      <dl v-if="updatedUser" class="mt-8 grid grid-cols-2 gap-3 rounded-2xl bg-gray-50 p-5 text-sm">
        <dt class="text-gray-500">Email</dt>
        <dd class="font-medium">{{ updatedUser.email }}</dd>
        <dt class="text-gray-500">Vai trò</dt>
        <dd class="font-medium">{{ updatedUser.role }}</dd>
      </dl>
    </section>
  </main>
</template>
