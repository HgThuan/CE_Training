<script setup lang="ts">
import { ref, computed } from 'vue'

import { formatVnd } from '@/shared/lib/formatters'

import FlashSaleForm from '../../components/FlashSaleForm.vue'
import { usePromotionStore } from '../../store'
import type { FlashSale, FlashSalePayload } from '../../types'
import ConfirmDialog from '@/shared/components/ConfirmDialog.vue'

const store = usePromotionStore()
const formOpen = ref(false)
const editing = ref<FlashSale | null>(null)
const confirmOpen = ref(false)
const confirmTarget = ref<FlashSale | null>(null)

const statusFilter = ref('')
const sortOrder = ref('desc')
const searchQuery = ref('')

const filteredSales = computed(() => {
  let result = store.flashSales
  if (statusFilter.value) {
    result = result.filter(s => s.status === statusFilter.value)
  }
  if (searchQuery.value) {
    const lower = searchQuery.value.toLowerCase()
    result = result.filter(s => s.name.toLowerCase().includes(lower) || s.items.some(i => i.product_name?.toLowerCase().includes(lower)))
  }
  return result.slice().sort((a, b) => {
    const timeA = new Date(a.start_time).getTime()
    const timeB = new Date(b.start_time).getTime()
    return sortOrder.value === 'desc' ? timeB - timeA : timeA - timeB
  })
})

const stats = computed(() => {
  const total = store.flashSales.length
  const ongoing = store.flashSales.filter(s => s.status === 'ongoing').length
  let totalProductsSold = 0
  let estimatedRevenue = 0
  store.flashSales.forEach(s => {
    s.items.forEach(i => {
      totalProductsSold += i.sold_count
      estimatedRevenue += i.sold_count * Number(i.sale_price)
    })
  })
  return { total, ongoing, totalProductsSold, estimatedRevenue }
})

function getStatusLabel(status: string) {
  if (status === 'ongoing') return 'Đang diễn ra'
  if (status === 'upcoming') return 'Sắp diễn ra'
  if (status === 'ended') return 'Đã kết thúc'
  return status
}

function getStatusColor(status: string) {
  if (status === 'ongoing') return 'bg-emerald-100 text-emerald-700'
  if (status === 'upcoming') return 'bg-amber-100 text-amber-700'
  return 'bg-slate-100 text-slate-700'
}

function open(sale: FlashSale | null = null): void {
  editing.value = sale
  formOpen.value = true
}
async function save(payload: FlashSalePayload): Promise<void> {
  await store.saveFlashSale(payload, editing.value?.id)
  formOpen.value = false
}
function requestRemove(sale: FlashSale): void {
  confirmTarget.value = sale
  confirmOpen.value = true
}
async function handleConfirmRemove(): Promise<void> {
  if (!confirmTarget.value) return
  await store.deleteFlashSale(confirmTarget.value.id)
  confirmOpen.value = false
  confirmTarget.value = null
}
function handleCancelRemove(): void {
  confirmOpen.value = false
  confirmTarget.value = null
}
void store.loadAdminFlashSales()
</script>

<template>
  <main class="mx-auto max-w-7xl px-4 py-8 sm:px-6">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="text-3xl font-black">Quản lý Flash Sale</h1>
        <p class="mt-2 text-slate-500">Khung giờ, giá sale và quota được kiểm soát tại máy chủ.</p>
      </div>
      <button class="rounded-xl bg-indigo-600 px-5 py-3 font-bold text-white" @click="open()">
        Tạo Flash Sale
      </button>
    </div>

    <div v-if="!store.loading && !store.error" class="mt-6 grid gap-4 sm:grid-cols-4">
      <div class="rounded-2xl border bg-white p-4 shadow-sm">
        <p class="text-sm font-bold text-slate-500">Tổng chương trình</p>
        <p class="mt-1 text-2xl font-black">{{ stats.total }}</p>
      </div>
      <div class="rounded-2xl border bg-white p-4 shadow-sm">
        <p class="text-sm font-bold text-slate-500">Đang diễn ra</p>
        <p class="mt-1 text-2xl font-black text-emerald-600">{{ stats.ongoing }}</p>
      </div>
      <div class="rounded-2xl border bg-white p-4 shadow-sm">
        <p class="text-sm font-bold text-slate-500">Đã bán</p>
        <p class="mt-1 text-2xl font-black text-indigo-600">{{ stats.totalProductsSold }}</p>
      </div>
      <div class="rounded-2xl border bg-white p-4 shadow-sm">
        <p class="text-sm font-bold text-slate-500">Doanh thu ước tính</p>
        <p class="mt-1 text-2xl font-black text-amber-600">{{ formatVnd(stats.estimatedRevenue) }}</p>
      </div>
    </div>

    <div v-if="!store.loading && !store.error" class="mt-6 flex flex-wrap gap-3 rounded-2xl bg-slate-50 p-4">
      <input
        v-model="searchQuery"
        placeholder="Tìm tên chương trình, sản phẩm..."
        class="min-w-[200px] flex-1 rounded-xl border px-4 py-2"
      />
      <select v-model="statusFilter" class="rounded-xl border px-4 py-2">
        <option value="">Tất cả trạng thái</option>
        <option value="ongoing">Đang diễn ra</option>
        <option value="upcoming">Sắp diễn ra</option>
        <option value="ended">Đã kết thúc</option>
      </select>
      <select v-model="sortOrder" class="rounded-xl border px-4 py-2">
        <option value="desc">Mới nhất</option>
        <option value="asc">Cũ nhất</option>
      </select>
    </div>
    <div v-if="store.loading" class="mt-7 h-52 animate-pulse rounded-3xl bg-slate-200" />
    <section v-else-if="store.error" class="mt-7 rounded-3xl bg-rose-50 p-8 text-center">
      <p class="font-bold text-rose-800">{{ store.error }}</p>
      <button
        class="mt-4 rounded-xl bg-rose-700 px-4 py-2 font-bold text-white"
        @click="store.loadAdminFlashSales"
      >
        Thử lại
      </button>
    </section>
    <section
      v-else-if="!store.flashSales.length"
      class="mt-7 rounded-3xl border border-dashed bg-white p-12 text-center text-slate-500"
    >
      Chưa có chương trình Flash Sale.
    </section>
    <div v-else class="mt-7 grid items-start gap-5 lg:grid-cols-2">
      <article
        v-for="sale in filteredSales"
        :key="sale.id"
        class="flex flex-col rounded-3xl border bg-white p-5 shadow-sm"
      >
        <div class="flex items-start justify-between gap-3">
          <div>
            <span :class="['rounded-full px-2 py-1 text-xs font-bold', getStatusColor(sale.status)]">{{
              getStatusLabel(sale.status)
            }}</span>
            <h2 class="mt-3 text-xl font-black">{{ sale.name }}</h2>
            <p class="mt-1 text-sm text-slate-500">
              {{ new Date(sale.start_time).toLocaleString('vi-VN') }} –
              {{ new Date(sale.end_time).toLocaleString('vi-VN') }}
            </p>
          </div>
          <div>
            <button class="mr-3 font-bold text-indigo-700" @click="open(sale)">Sửa</button
            ><button class="font-bold text-rose-700" @click="requestRemove(sale)">Xóa</button>
          </div>
        </div>
        <ul class="mt-4 max-h-[300px] divide-y overflow-y-auto rounded-2xl bg-slate-50 px-4">
          <li
            v-for="item in sale.items"
            :key="item.id"
            class="flex justify-between gap-3 py-3 text-sm"
          >
            <div class="min-w-0 flex-1 pr-4">
              <p class="truncate font-semibold">{{ item.product_name || 'Sản phẩm' }}</p>
              <p class="truncate text-xs text-slate-500">Phân loại: {{ item.variant_sku || item.variant || 'Mặc định' }}</p>
            </div>
            <div class="flex flex-col items-end gap-1">
              <strong class="text-indigo-700">{{ formatVnd(item.sale_price) }}</strong>
              <div class="flex w-24 items-center gap-2 text-xs">
                <div class="h-2 flex-1 overflow-hidden rounded-full bg-slate-200">
                  <div class="h-full rounded-full bg-rose-500" :style="{ width: Math.min(100, (item.sold_count / item.quota) * 100) + '%' }"></div>
                </div>
                <span class="whitespace-nowrap text-slate-500">{{ item.sold_count }}/{{ item.quota }}</span>
              </div>
            </div>
          </li>
        </ul>
      </article>
    </div>
    <div
      v-if="formOpen"
      class="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-slate-950/60 p-4"
      @click.self="formOpen = false"
    >
      <div class="my-8 w-full max-w-4xl rounded-3xl bg-white p-6">
        <h2 class="mb-5 text-xl font-black">
          {{ editing ? 'Cập nhật Flash Sale' : 'Tạo Flash Sale' }}
        </h2>
        <FlashSaleForm
          :key="editing?.id ?? 'new'"
          :flash-sale="editing"
          :saving="store.saving"
          @submit="save"
          @cancel="formOpen = false"
        />
      </div>
    </div>
    
    <ConfirmDialog
      :open="confirmOpen"
      title="Xóa Flash Sale"
      :message="'Bạn có chắc chắn muốn xóa chương trình ' + confirmTarget?.name + '?'"
      @confirm="handleConfirmRemove"
      @cancel="handleCancelRemove"
    />
  </main>
</template>
