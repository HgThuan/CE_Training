<script setup lang="ts">
import { onMounted, ref } from 'vue'

import FormMessage from '@/features/auth/components/FormMessage.vue'
import { getErrorMessage } from '@/features/auth/errors'
import { promptDialog } from '@/shared/composables/useAppDialog'
import type { PaginationMeta } from '@/shared/types/api'

import { adminSellersApi } from '../api'
import type { AdminSeller } from '../types'

const sellers = ref<AdminSeller[]>([])
const search = ref('')
const shopStatus = ref<'all' | 'approved' | 'locked'>('all')
const meta = ref<PaginationMeta>({ page: 1, page_size: 20, total_items: 0, total_pages: 0 })
const loading = ref(true)
const message = ref('')
const errorMessage = ref('')

async function loadSellers(page = 1): Promise<void> {
  loading.value = true
  try {
    const response = await adminSellersApi.listSellers({
      search: search.value || undefined,
      shop__status: shopStatus.value === 'all' ? undefined : shopStatus.value,
      page,
      page_size: meta.value.page_size,
    })
    sellers.value = response.data.data
    if (response.data.meta) meta.value = response.data.meta
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
}

async function toggleShop(seller: AdminSeller): Promise<void> {
  if (!seller.shop) return
  const locking = seller.shop.status !== 'locked'
  const reason = await promptDialog({
    title: locking ? 'Khóa gian hàng' : 'Mở khóa gian hàng',
    inputLabel: locking ? 'Lý do khóa gian hàng' : 'Ghi chú mở khóa',
    confirmLabel: locking ? 'Khóa gian hàng' : 'Mở khóa',
    destructive: locking,
    required: true,
  })
  if (!reason?.trim()) return
  try {
    const response = locking
      ? await adminSellersApi.lockShop(seller.shop.id, reason.trim())
      : await adminSellersApi.unlockShop(seller.shop.id, reason.trim())
    message.value = response.data.message
    await loadSellers(meta.value.page)
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
}

async function renameShop(seller: AdminSeller): Promise<void> {
  if (!seller.shop) return
  const name = await promptDialog({
    title: 'Đổi tên gian hàng',
    inputLabel: 'Tên gian hàng mới',
    initialValue: seller.shop.name,
    confirmLabel: 'Lưu tên',
    required: true,
  })
  if (!name?.trim() || name.trim() === seller.shop.name) return
  try {
    message.value = (
      await adminSellersApi.updateSellerShop(seller.id, { name: name.trim() })
    ).data.message
    await loadSellers(meta.value.page)
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
}

async function deleteSeller(seller: AdminSeller): Promise<void> {
  const reason = await promptDialog({
    title: 'Xóa seller',
    message: seller.email,
    inputLabel: 'Lý do xóa mềm',
    confirmLabel: 'Xóa seller',
    destructive: true,
    required: true,
  })
  if (!reason?.trim()) return
  try {
    message.value = (await adminSellersApi.deleteSeller(seller.id, reason.trim())).data.message
    await loadSellers(meta.value.page)
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
}

onMounted(loadSellers)
</script>

<template>
  <main class="mx-auto max-w-7xl px-4 py-10">
    <RouterLink class="font-semibold text-indigo-600" to="/admin">← Admin workspace</RouterLink>
    <h1 class="mt-5 text-3xl font-bold">Quản lý nhà bán hàng</h1>
    <FormMessage v-if="message" class="mt-6" :message="message" variant="success" />
    <FormMessage v-if="errorMessage" class="mt-6" :message="errorMessage" />
    <form class="mt-8 flex flex-wrap gap-3" @submit.prevent="loadSellers(1)">
      <input
        v-model.trim="search"
        class="min-w-64 flex-1 rounded-xl border px-3 py-2.5"
        placeholder="Email, họ tên, tên shop"
      />
      <select v-model="shopStatus" class="rounded-xl border px-3 py-2.5">
        <option value="all">Mọi trạng thái</option>
        <option value="approved">Đã duyệt</option>
        <option value="locked">Bị khóa</option>
      </select>
      <button class="rounded-xl bg-gray-950 px-5 py-2.5 font-bold text-white">Lọc</button>
    </form>
    <div class="mt-6 overflow-x-auto rounded-2xl bg-white ring-1 ring-gray-200">
      <table class="w-full min-w-3xl text-left text-sm">
        <thead class="bg-gray-50">
          <tr>
            <th class="p-4">Seller</th>
            <th>Shop</th>
            <th>Trạng thái</th>
            <th>Thao tác</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td class="p-4" colspan="4">Đang tải…</td>
          </tr>
          <tr v-for="seller in sellers" :key="seller.id" class="border-t">
            <td class="p-4">
              <strong>{{ seller.full_name || seller.email }}</strong
              ><br />{{ seller.email }}
            </td>
            <td>{{ seller.shop?.name ?? 'Chưa có shop' }}</td>
            <td>
              <span
                class="inline-flex rounded-full px-2 py-0.5 text-xs font-semibold leading-5"
                :class="{
                  'bg-green-100 text-green-800': (seller.shop?.status ?? seller.seller_profile.onboarding_status) === 'approved',
                  'bg-yellow-100 text-yellow-800': (seller.shop?.status ?? seller.seller_profile.onboarding_status) === 'pending',
                  'bg-red-100 text-red-800': (seller.shop?.status ?? seller.seller_profile.onboarding_status) === 'rejected',
                  'bg-gray-100 text-gray-800': (seller.shop?.status ?? seller.seller_profile.onboarding_status) === 'locked',
                }"
              >
                {{ { approved: 'Đã duyệt', pending: 'Chờ duyệt', rejected: 'Từ chối', locked: 'Bị khóa' }[seller.shop?.status ?? seller.seller_profile.onboarding_status] || (seller.shop?.status ?? seller.seller_profile.onboarding_status) }}
              </span>
            </td>
            <td class="space-x-2">
              <button
                v-if="seller.shop"
                class="font-semibold text-indigo-600"
                type="button"
                @click="renameShop(seller)"
              >
                Sửa
              </button>
              <button
                v-if="seller.shop"
                class="font-semibold text-amber-700"
                type="button"
                @click="toggleShop(seller)"
              >
                {{ seller.shop?.status === 'locked' ? 'Mở khóa' : 'Khóa shop' }}
              </button>
              <button
                class="font-semibold text-red-700"
                type="button"
                @click="deleteSeller(seller)"
              >
                Xóa
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="meta.total_pages > 1" class="flex items-center justify-between border-t p-4">
        <button class="rounded-lg border px-3 py-1.5 text-sm font-bold disabled:opacity-50" :disabled="meta.page <= 1" @click="loadSellers(meta.page - 1)" type="button">Trang trước</button>
        <span class="text-sm text-gray-500">Trang {{ meta.page }} / {{ meta.total_pages }}</span>
        <button class="rounded-lg border px-3 py-1.5 text-sm font-bold disabled:opacity-50" :disabled="meta.page >= meta.total_pages" @click="loadSellers(meta.page + 1)" type="button">Trang tiếp</button>
      </div>
    </div>
  </main>
</template>
