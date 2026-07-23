<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import FormMessage from '@/features/auth/components/FormMessage.vue'
import { getErrorMessage } from '@/features/auth/errors'
import type { PaginationMeta } from '@/shared/types/api'

import { adminUsersApi } from '../api'
import type { AdminCustomer, CustomerCreatePayload, CustomerUpdatePayload } from '../types'

const emptyCreateForm = (): CustomerCreatePayload => ({
  email: '',
  password: '',
  password_confirm: '',
  full_name: '',
  phone: '',
  date_of_birth: null,
  gender: '',
  is_email_verified: false,
})

const customers = ref<AdminCustomer[]>([])
const meta = ref<PaginationMeta>({ page: 1, page_size: 20, total_items: 0, total_pages: 1 })
const search = ref('')
const activeFilter = ref<'all' | 'active' | 'locked'>('all')
const loading = ref(true)
const saving = ref(false)
const showCreateForm = ref(false)
const selectedCustomer = ref<AdminCustomer | null>(null)
const createForm = reactive<CustomerCreatePayload>(emptyCreateForm())
const editForm = reactive<CustomerUpdatePayload>({})
const message = ref('')
const errorMessage = ref('')

async function loadCustomers(page = 1): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await adminUsersApi.listCustomers({
      search: search.value || undefined,
      is_active: activeFilter.value === 'all' ? undefined : activeFilter.value === 'active',
      page,
      page_size: meta.value.page_size,
    })
    customers.value = response.data.data
    if (response.data.meta) meta.value = response.data.meta
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
}

async function createCustomer(): Promise<void> {
  saving.value = true
  message.value = ''
  errorMessage.value = ''
  try {
    const response = await adminUsersApi.createCustomer({
      ...createForm,
      date_of_birth: createForm.date_of_birth || null,
    })
    message.value = response.data.message
    Object.assign(createForm, emptyCreateForm())
    showCreateForm.value = false
    await loadCustomers(1)
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    saving.value = false
  }
}

async function selectCustomer(customer: AdminCustomer): Promise<void> {
  errorMessage.value = ''
  try {
    const response = await adminUsersApi.getCustomer(customer.id)
    selectedCustomer.value = response.data.data
    Object.assign(editForm, {
      email: response.data.data.email,
      full_name: response.data.data.full_name,
      phone: response.data.data.phone,
      date_of_birth: response.data.data.date_of_birth ?? null,
      gender: response.data.data.gender ?? '',
      is_email_verified: response.data.data.is_email_verified,
    })
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
}

async function updateCustomer(): Promise<void> {
  if (!selectedCustomer.value) return
  saving.value = true
  errorMessage.value = ''
  try {
    const response = await adminUsersApi.updateCustomer(selectedCustomer.value.id, {
      ...editForm,
    })
    selectedCustomer.value = response.data.data
    message.value = response.data.message
    await loadCustomers(meta.value.page)
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    saving.value = false
  }
}

async function toggleAccount(customer: AdminCustomer): Promise<void> {
  const action = customer.is_active ? 'khóa' : 'mở khóa'
  const reason = window.prompt(`Nhập lý do ${action} tài khoản ${customer.email}:`)
  if (!reason?.trim()) return
  errorMessage.value = ''
  try {
    const response = customer.is_active
      ? await adminUsersApi.lockUser(customer.id, reason.trim())
      : await adminUsersApi.unlockUser(customer.id, reason.trim())
    message.value = response.data.message
    await loadCustomers(meta.value.page)
    if (selectedCustomer.value?.id === customer.id) await selectCustomer(customer)
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
}

async function resetPassword(customer: AdminCustomer): Promise<void> {
  if (!window.confirm(`Gửi liên kết đặt lại mật khẩu cho ${customer.email}?`)) return
  const reason = window.prompt('Ghi chú/lý do hỗ trợ:', '') ?? ''
  errorMessage.value = ''
  try {
    const response = await adminUsersApi.resetPassword(customer.id, reason)
    message.value = response.data.message
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
}

async function removeCustomer(customer: AdminCustomer): Promise<void> {
  if (!window.confirm(`Xóa mềm khách hàng ${customer.email}?`)) return
  errorMessage.value = ''
  try {
    const response = await adminUsersApi.deleteCustomer(customer.id)
    message.value = response.data.message
    if (selectedCustomer.value?.id === customer.id) selectedCustomer.value = null
    await loadCustomers(meta.value.page)
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
}

onMounted(() => loadCustomers())
</script>

<template>
  <main class="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-12">
    <header class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <RouterLink class="font-semibold text-indigo-600" to="/admin">← Admin workspace</RouterLink>
        <p class="mt-5 text-sm font-bold uppercase tracking-[0.2em] text-indigo-600">
          ADM-04 · ADM-06 · ADM-07
        </p>
        <h1 class="mt-2 text-3xl font-bold text-gray-950">Quản lý khách hàng</h1>
      </div>
      <button
        class="rounded-xl bg-indigo-600 px-4 py-3 font-semibold text-white"
        type="button"
        @click="showCreateForm = !showCreateForm"
      >
        {{ showCreateForm ? 'Đóng biểu mẫu' : 'Tạo khách hàng' }}
      </button>
    </header>

    <FormMessage v-if="message" class="mt-6" :message="message" variant="success" />
    <FormMessage v-if="errorMessage" class="mt-6" :message="errorMessage" />

    <form
      v-if="showCreateForm"
      class="mt-8 grid gap-4 rounded-2xl bg-white p-5 ring-1 ring-gray-200 sm:grid-cols-2 sm:p-6"
      @submit.prevent="createCustomer"
    >
      <h2 class="text-xl font-bold sm:col-span-2">Tạo khách hàng mới</h2>
      <label class="text-sm font-medium"
        >Email<input
          v-model.trim="createForm.email"
          class="mt-2 w-full rounded-xl border px-3 py-2.5"
          type="email"
          required
      /></label>
      <label class="text-sm font-medium"
        >Họ tên<input
          v-model.trim="createForm.full_name"
          class="mt-2 w-full rounded-xl border px-3 py-2.5"
          required
      /></label>
      <label class="text-sm font-medium"
        >Số điện thoại<input
          v-model.trim="createForm.phone"
          class="mt-2 w-full rounded-xl border px-3 py-2.5"
          inputmode="tel"
      /></label>
      <label class="text-sm font-medium"
        >Ngày sinh<input
          v-model="createForm.date_of_birth"
          class="mt-2 w-full rounded-xl border px-3 py-2.5"
          type="date"
      /></label>
      <label class="text-sm font-medium"
        >Mật khẩu ban đầu<input
          v-model="createForm.password"
          class="mt-2 w-full rounded-xl border px-3 py-2.5"
          autocomplete="new-password"
          type="password"
          minlength="8"
          required
        />
        <span class="mt-1 block text-xs font-normal text-gray-500">
          Tối thiểu 8 ký tự, không dùng mật khẩu phổ biến hoặc chỉ gồm chữ số.
        </span></label
      >
      <label class="text-sm font-medium"
        >Xác nhận mật khẩu<input
          v-model="createForm.password_confirm"
          class="mt-2 w-full rounded-xl border px-3 py-2.5"
          autocomplete="new-password"
          type="password"
          required
      /></label>
      <label class="text-sm font-medium"
        >Giới tính<select
          v-model="createForm.gender"
          class="mt-2 w-full rounded-xl border px-3 py-2.5"
        >
          <option value="">Không cung cấp</option>
          <option value="male">Nam</option>
          <option value="female">Nữ</option>
          <option value="other">Khác</option>
        </select></label
      >
      <label class="flex items-center gap-3 self-end pb-3 text-sm font-medium"
        ><input v-model="createForm.is_email_verified" class="size-4" type="checkbox" />Đánh dấu
        email đã xác thực</label
      >
      <button
        class="rounded-xl bg-gray-950 px-4 py-3 font-semibold text-white disabled:opacity-60 sm:col-span-2"
        :disabled="saving"
        type="submit"
      >
        {{ saving ? 'Đang tạo…' : 'Tạo khách hàng' }}
      </button>
    </form>

    <section class="mt-8 rounded-2xl bg-white p-5 ring-1 ring-gray-200 sm:p-6">
      <form
        class="grid gap-3 sm:grid-cols-[minmax(0,1fr)_12rem_auto]"
        @submit.prevent="loadCustomers(1)"
      >
        <input
          v-model.trim="search"
          aria-label="Tìm khách hàng"
          class="rounded-xl border px-4 py-2.5"
          placeholder="Tìm theo tên, email, SĐT"
        />
        <select
          v-model="activeFilter"
          aria-label="Trạng thái"
          class="rounded-xl border px-4 py-2.5"
        >
          <option value="all">Mọi trạng thái</option>
          <option value="active">Đang hoạt động</option>
          <option value="locked">Đã khóa</option>
        </select>
        <button class="rounded-xl bg-indigo-600 px-5 py-2.5 font-semibold text-white" type="submit">
          Tìm kiếm
        </button>
      </form>

      <p v-if="loading" class="py-10 text-center text-gray-600">Đang tải khách hàng…</p>
      <div v-else class="mt-6 overflow-x-auto">
        <table class="min-w-full text-left text-sm">
          <thead class="border-b text-gray-500">
            <tr>
              <th class="px-3 py-3">Khách hàng</th>
              <th class="px-3 py-3">Trạng thái</th>
              <th class="px-3 py-3">Ngày tạo</th>
              <th class="px-3 py-3 text-right">Thao tác</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="customer in customers"
              :key="customer.id"
              class="border-b border-gray-100 align-top"
            >
              <td class="px-3 py-4">
                <button
                  class="text-left font-bold text-indigo-700"
                  type="button"
                  @click="selectCustomer(customer)"
                >
                  {{ customer.full_name || 'Chưa có tên' }}
                </button>
                <p class="mt-1 text-gray-600">{{ customer.email }}</p>
                <p class="text-gray-500">{{ customer.phone || 'Chưa có SĐT' }}</p>
              </td>
              <td class="px-3 py-4">
                <span
                  :class="
                    customer.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'
                  "
                  class="rounded-full px-2.5 py-1 text-xs font-bold"
                  >{{ customer.is_active ? 'Hoạt động' : 'Đã khóa' }}</span
                >
              </td>
              <td class="whitespace-nowrap px-3 py-4 text-gray-600">
                {{ new Date(customer.created_at).toLocaleDateString('vi-VN') }}
              </td>
              <td class="px-3 py-4">
                <div class="flex min-w-max justify-end gap-2">
                  <button
                    class="rounded-lg border px-3 py-2 font-semibold"
                    type="button"
                    @click="toggleAccount(customer)"
                  >
                    {{ customer.is_active ? 'Khóa' : 'Mở khóa' }}</button
                  ><button
                    class="rounded-lg border px-3 py-2 font-semibold"
                    type="button"
                    :disabled="!customer.is_active"
                    @click="resetPassword(customer)"
                  >
                    Reset MK</button
                  ><button
                    class="rounded-lg border border-red-200 px-3 py-2 font-semibold text-red-700"
                    type="button"
                    @click="removeCustomer(customer)"
                  >
                    Xóa
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <footer class="mt-5 flex flex-wrap items-center justify-between gap-3 text-sm text-gray-600">
        <span
          >{{ meta.total_items }} khách hàng · Trang {{ meta.page }}/{{ meta.total_pages }}</span
        >
        <div class="flex gap-2">
          <button
            class="rounded-lg border px-3 py-2 disabled:opacity-40"
            :disabled="meta.page <= 1"
            type="button"
            @click="loadCustomers(meta.page - 1)"
          >
            Trước</button
          ><button
            class="rounded-lg border px-3 py-2 disabled:opacity-40"
            :disabled="meta.page >= meta.total_pages"
            type="button"
            @click="loadCustomers(meta.page + 1)"
          >
            Sau
          </button>
        </div>
      </footer>
    </section>

    <form
      v-if="selectedCustomer"
      class="mt-8 grid gap-4 rounded-2xl bg-white p-5 ring-1 ring-gray-200 sm:grid-cols-2 sm:p-6"
      @submit.prevent="updateCustomer"
    >
      <div class="flex items-center justify-between sm:col-span-2">
        <div>
          <h2 class="text-xl font-bold">Chi tiết khách hàng #{{ selectedCustomer.id }}</h2>
          <p v-if="selectedCustomer.lock_reason" class="mt-1 text-sm text-red-700">
            Lý do khóa: {{ selectedCustomer.lock_reason }}
          </p>
        </div>
        <button class="font-semibold text-gray-600" type="button" @click="selectedCustomer = null">
          Đóng
        </button>
      </div>
      <label class="text-sm font-medium"
        >Email<input
          v-model.trim="editForm.email"
          class="mt-2 w-full rounded-xl border px-3 py-2.5"
          type="email"
          required
      /></label>
      <label class="text-sm font-medium"
        >Họ tên<input
          v-model.trim="editForm.full_name"
          class="mt-2 w-full rounded-xl border px-3 py-2.5"
      /></label>
      <label class="text-sm font-medium"
        >Số điện thoại<input
          v-model.trim="editForm.phone"
          class="mt-2 w-full rounded-xl border px-3 py-2.5"
      /></label>
      <label class="text-sm font-medium"
        >Ngày sinh<input
          v-model="editForm.date_of_birth"
          class="mt-2 w-full rounded-xl border px-3 py-2.5"
          type="date"
      /></label>
      <label class="text-sm font-medium"
        >Giới tính<select
          v-model="editForm.gender"
          class="mt-2 w-full rounded-xl border px-3 py-2.5"
        >
          <option value="">Không cung cấp</option>
          <option value="male">Nam</option>
          <option value="female">Nữ</option>
          <option value="other">Khác</option>
        </select></label
      >
      <label class="flex items-center gap-3 self-end pb-3 text-sm font-medium"
        ><input v-model="editForm.is_email_verified" class="size-4" type="checkbox" />Email đã xác
        thực</label
      >
      <button
        class="rounded-xl bg-gray-950 px-4 py-3 font-semibold text-white disabled:opacity-60 sm:col-span-2"
        :disabled="saving"
        type="submit"
      >
        {{ saving ? 'Đang lưu…' : 'Lưu thông tin khách hàng' }}
      </button>
    </form>
  </main>
</template>
