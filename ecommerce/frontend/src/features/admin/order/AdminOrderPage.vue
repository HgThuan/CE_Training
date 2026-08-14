<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { orderApi } from '@/features/order/api'
import type { CommerceOrder } from '@/features/order/types'
import { formatCurrency } from '@/shared/lib/formatters'
import type { PaginationMeta } from '@/shared/types/api'

const orders = ref<CommerceOrder[]>([])
const loading = ref(true)
const error = ref('')
const meta = ref<PaginationMeta>({ page: 1, page_size: 20, total_items: 0, total_pages: 0 })
const filters = reactive({ status: '', search: '', date_from: '', date_to: '' })

const statusLabels: Record<string, string> = {
  PENDING: 'Chờ thanh toán',
  PAID: 'Đã thanh toán',
  EXPIRED: 'Đã hết hạn',
  PENDING_CONFIRMATION: 'Chờ xác nhận',
  CONFIRMED: 'Đã xác nhận',
  PACKING: 'Đang đóng gói',
  SHIPPING: 'Đang giao',
  DELIVERED: 'Đã giao',
  COMPLETED: 'Hoàn thành',
  CANCELLED: 'Đã hủy',
  REFUND_PENDING: 'Chờ hoàn tiền',
  RETURN_REJECTED: 'Từ chối hoàn hàng',
}

function statusLabel(value: string): string {
  return statusLabels[value] ?? value.replaceAll('_', ' ')
}
function statusClass(value: string): string {
  if (['COMPLETED', 'PAID', 'DELIVERED'].includes(value)) return 'bg-emerald-50 text-emerald-700'
  if (['CANCELLED', 'EXPIRED', 'RETURN_REJECTED'].includes(value)) return 'bg-rose-50 text-rose-700'
  if (value.includes('REFUND')) return 'bg-orange-100 text-orange-800 ring-1 ring-orange-300'
  return 'bg-amber-50 text-amber-700'
}

const summary = computed(() => ({
  total: meta.value.total_items,
  pending: orders.value.filter((order) =>
    order.shop_orders.some((item) => item.fulfillment_status.includes('PENDING')),
  ).length,
  refunds: orders.value.filter((order) =>
    order.shop_orders.some((item) => item.fulfillment_status.includes('REFUND')),
  ).length,
}))

async function load(page = 1): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const response = await orderApi.adminOrders({
      ...Object.fromEntries(Object.entries(filters).filter(([, value]) => value)),
      page,
      page_size: meta.value.page_size,
    })
    orders.value = response.data.data
    if (response.data.meta) meta.value = response.data.meta
  } catch {
    error.value = 'Không thể tải dữ liệu đơn hàng. Vui lòng thử lại.'
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>

<template>
  <main class="mx-auto max-w-7xl px-4 py-8 sm:px-6">
    <h1 class="text-3xl font-black">Giám sát đơn hàng</h1>
    <p class="mt-2 text-slate-600">Theo dõi trạng thái vận hành và ưu tiên các đơn cần xử lý.</p>
    <section class="mt-6 grid gap-3 sm:grid-cols-3">
      <div class="rounded-2xl bg-white p-4 ring-1 ring-slate-200">
        <p class="text-sm text-slate-500">Tổng đơn</p>
        <strong class="text-2xl">{{ summary.total }}</strong>
      </div>
      <div class="rounded-2xl bg-white p-4 ring-1 ring-slate-200">
        <p class="text-sm text-slate-500">Đang chờ trên trang này</p>
        <strong class="text-2xl text-amber-700">{{ summary.pending }}</strong>
      </div>
      <div class="rounded-2xl bg-white p-4 ring-1 ring-slate-200">
        <p class="text-sm text-slate-500">Cần xử lý hoàn tiền</p>
        <strong class="text-2xl text-orange-700">{{ summary.refunds }}</strong>
      </div>
    </section>
    <form class="my-5 grid gap-3 rounded-2xl bg-white p-4 md:grid-cols-5" @submit.prevent="load(1)">
      <input
        v-model="filters.search"
        class="rounded-xl border border-slate-300 p-3"
        placeholder="Mã đơn / khách"
      />
      <select v-model="filters.status" class="rounded-xl border border-slate-300 bg-white p-3">
        <option value="">Mọi trạng thái</option>
        <option v-for="(label, value) in statusLabels" :key="value" :value="value">
          {{ label }}
        </option>
      </select>
      <label class="text-xs font-bold text-slate-600"
        >Từ ngày<input
          v-model="filters.date_from"
          type="date"
          class="mt-1 w-full rounded-xl border border-slate-300 p-3"
      /></label>
      <label class="text-xs font-bold text-slate-600"
        >Đến ngày<input
          v-model="filters.date_to"
          type="date"
          class="mt-1 w-full rounded-xl border border-slate-300 p-3"
      /></label>
      <button class="rounded-xl bg-slate-950 px-4 py-3 font-bold text-white">Áp dụng bộ lọc</button>
    </form>
    <p v-if="loading" class="py-12 text-center text-slate-500">Đang tải đơn hàng…</p>
    <div v-else-if="error" class="rounded-2xl bg-rose-50 p-6 text-center text-rose-700">
      <p>{{ error }}</p>
      <button class="mt-3 font-bold underline" @click="load(meta.page)">Thử lại</button>
    </div>
    <div v-else class="overflow-x-auto rounded-2xl bg-white shadow-sm ring-1 ring-slate-200">
      <table class="w-full min-w-[1050px] text-left text-sm">
        <thead class="bg-slate-50">
          <tr>
            <th class="p-4">Đơn hàng</th>
            <th>Phương thức</th>
            <th>Thanh toán</th>
            <th>Đơn theo shop</th>
            <th>Tổng</th>
            <th>Ngày đặt</th>
            <th class="pr-4 text-right">Thao tác</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="order in orders"
            :key="order.id"
            class="border-t align-middle"
            :class="
              order.shop_orders.some((item) => item.fulfillment_status.includes('REFUND'))
                ? 'bg-orange-50/60'
                : ''
            "
          >
            <td class="p-4 font-mono font-bold">{{ order.order_code }}</td>
            <td class="py-4">{{ order.payment_method }}</td>
            <td class="py-4">
              <span
                class="rounded-full px-2.5 py-1 text-xs font-bold"
                :class="statusClass(order.payment_status)"
                >{{ statusLabel(order.payment_status) }}</span
              >
            </td>
            <td class="max-w-xs py-4">
              <div class="flex flex-wrap gap-1.5">
                <span
                  v-for="shop in order.shop_orders"
                  :key="shop.id"
                  class="rounded-lg bg-slate-100 px-2 py-1 text-xs"
                  >{{ shop.shop_name }} ·
                  <b :class="statusClass(shop.fulfillment_status)">{{
                    statusLabel(shop.fulfillment_status)
                  }}</b></span
                >
              </div>
            </td>
            <td class="py-4 font-bold">{{ formatCurrency(order.grand_total) }}</td>
            <td class="py-4">{{ new Date(order.placed_at).toLocaleString('vi-VN') }}</td>
            <td class="py-4 pr-4 text-right">
              <RouterLink class="font-bold text-indigo-700" :to="`/admin/orders/${order.id}`"
                >Xem chi tiết</RouterLink
              >
            </td>
          </tr>
          <tr v-if="!orders.length">
            <td colspan="7" class="p-10 text-center text-slate-500">Không có đơn hàng phù hợp.</td>
          </tr>
        </tbody>
      </table>
    </div>
    <nav v-if="meta.total_pages > 1" class="mt-5 flex items-center justify-between text-sm">
      <span>Trang {{ meta.page }}/{{ meta.total_pages }} · {{ meta.total_items }} đơn</span>
      <div class="flex gap-2">
        <button
          class="rounded-xl border px-4 py-2 disabled:opacity-40"
          :disabled="meta.page <= 1"
          @click="load(meta.page - 1)"
        >
          Trang trước</button
        ><button
          class="rounded-xl border px-4 py-2 disabled:opacity-40"
          :disabled="meta.page >= meta.total_pages"
          @click="load(meta.page + 1)"
        >
          Trang sau
        </button>
      </div>
    </nav>
  </main>
</template>
