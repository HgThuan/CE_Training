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
const statusLabels: Record<string, string> = {
  pending: 'Chờ duyệt',
  approved: 'Đang hoạt động',
  rejected: 'Đã từ chối',
  locked: 'Bị khóa',
}
function statusClass(status: string): string {
  return status === 'approved'
    ? 'bg-emerald-50 text-emerald-700'
    : status === 'rejected' || status === 'locked'
      ? 'bg-rose-50 text-rose-700'
      : 'bg-amber-50 text-amber-700'
}

async function loadSellers(page = 1): Promise<void> {
  loading.value = true
  errorMessage.value = ''
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
    message: seller.shop.name,
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
    inputLabel: 'Lý do xóa seller',
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
  <FormMessage v-if="message" class="mt-5" :message="message" variant="success" />
  <FormMessage v-if="errorMessage" class="mt-5" :message="errorMessage" />
  <form
    class="mt-5 grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto_auto]"
    @submit.prevent="loadSellers(1)"
  >
    <input
      v-model.trim="search"
      class="rounded-xl border border-slate-300 bg-white px-4 py-3 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
      placeholder="Tìm theo email, họ tên hoặc tên shop"
    />
    <select v-model="shopStatus" class="rounded-xl border border-slate-300 bg-white px-4 py-3">
      <option value="all">Mọi trạng thái</option>
      <option value="approved">Đang hoạt động</option>
      <option value="locked">Bị khóa</option>
    </select>
    <button class="rounded-xl bg-slate-950 px-6 py-3 font-bold text-white hover:bg-slate-800">
      Tìm seller
    </button>
  </form>
  <div class="mt-5 overflow-x-auto rounded-2xl bg-white ring-1 ring-slate-200">
    <table class="w-full min-w-[860px] text-left text-sm">
      <thead class="bg-slate-50 text-slate-600">
        <tr>
          <th class="p-4">Seller</th>
          <th class="p-4">Gian hàng</th>
          <th class="p-4">Trạng thái</th>
          <th class="p-4 text-right">Thao tác</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-slate-100">
        <tr v-if="loading">
          <td class="p-8 text-center text-slate-500" colspan="4">Đang tải seller…</td>
        </tr>
        <tr v-for="seller in sellers" :key="seller.id" class="align-middle">
          <td class="p-4">
            <strong class="block text-slate-950">{{ seller.full_name || seller.email }}</strong
            ><span class="mt-1 block text-slate-500">{{ seller.email }}</span>
          </td>
          <td class="p-4">
            <strong v-if="seller.shop">{{ seller.shop.name }}</strong
            ><span v-else class="text-slate-500">Chưa có gian hàng</span>
          </td>
          <td class="p-4">
            <span
              class="rounded-full px-2.5 py-1 text-xs font-bold"
              :class="statusClass(seller.shop?.status ?? seller.seller_profile.onboarding_status)"
              >{{
                statusLabels[seller.shop?.status ?? seller.seller_profile.onboarding_status]
              }}</span
            >
          </td>
          <td class="p-4 text-right">
            <div class="flex justify-end gap-3">
              <button
                v-if="seller.shop"
                class="font-bold text-indigo-700"
                type="button"
                @click="renameShop(seller)"
              >
                Đổi tên</button
              ><button
                v-if="seller.shop"
                class="font-bold"
                :class="seller.shop.status === 'locked' ? 'text-emerald-700' : 'text-amber-700'"
                type="button"
                @click="toggleShop(seller)"
              >
                {{ seller.shop.status === 'locked' ? 'Mở khóa' : 'Khóa shop' }}</button
              ><button class="font-bold text-rose-700" type="button" @click="deleteSeller(seller)">
                Xóa
              </button>
            </div>
          </td>
        </tr>
        <tr v-if="!loading && !sellers.length">
          <td class="p-10 text-center text-slate-500" colspan="4">Không có seller phù hợp.</td>
        </tr>
      </tbody>
    </table>
  </div>
  <nav
    v-if="meta.total_pages > 1"
    class="mt-5 flex flex-wrap items-center justify-between gap-3 text-sm"
  >
    <span>Trang {{ meta.page }}/{{ meta.total_pages }} · {{ meta.total_items }} seller</span>
    <div class="flex gap-2">
      <button
        class="rounded-xl border border-slate-300 px-4 py-2 disabled:opacity-40"
        :disabled="meta.page <= 1"
        @click="loadSellers(meta.page - 1)"
      >
        Trang trước</button
      ><button
        class="rounded-xl border border-slate-300 px-4 py-2 disabled:opacity-40"
        :disabled="meta.page >= meta.total_pages"
        @click="loadSellers(meta.page + 1)"
      >
        Trang sau
      </button>
    </div>
  </nav>
</template>
