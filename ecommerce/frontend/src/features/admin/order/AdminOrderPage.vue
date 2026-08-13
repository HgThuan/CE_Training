<script setup lang="ts">
import { onMounted, reactive, ref, computed } from 'vue'
import { formatCurrency } from '@/shared/lib/formatters'
import { orderApi } from '@/features/order/api'
import type { CommerceOrder } from '@/features/order/types'

const orders = ref<CommerceOrder[]>([])
const loading = ref(true)
const error = ref('')
const filters = reactive({ status: '', search: '', date_from: '', date_to: '' })

const totalOrders = computed(() => orders.value.length)
const pendingOrders = computed(() => orders.value.filter(o => o.shop_orders.some(s => s.fulfillment_status === 'PENDING_CONFIRMATION')).length)

async function load() {
  loading.value = true
  try {
    const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v))
    const response = await orderApi.adminOrders(params)
    orders.value = response.data.data
  } catch {
    error.value = 'Không thể tải dữ liệu đơn hàng.'
  } finally {
    loading.value = false
  }
}

onMounted(load)

function translateStatus(status: string) {
  const map: Record<string, string> = {
    PENDING_CONFIRMATION: 'Chờ xác nhận',
    CONFIRMED: 'Đã xác nhận',
    SHIPPING: 'Đang giao',
    COMPLETED: 'Hoàn thành',
    CANCELLED: 'Đã hủy',
    EXPIRED: 'Hết hạn',
    RETURN_REJECTED: 'Từ chối trả',
    REFUND_PENDING: 'Chờ hoàn tiền'
  }
  return map[status] || status
}

function getStatusColor(status: string) {
  if (['COMPLETED', 'CONFIRMED'].includes(status)) return 'bg-green-100 text-green-800'
  if (['CANCELLED', 'EXPIRED', 'RETURN_REJECTED'].includes(status)) return 'bg-red-100 text-red-800'
  if (status === 'REFUND_PENDING') return 'bg-rose-500 text-white animate-pulse shadow-sm'
  return 'bg-yellow-100 text-yellow-800'
}
</script>

<template>
  <main class="mx-auto max-w-7xl px-4 py-8">
    <h1 class="text-3xl font-black">Giám sát đơn hàng</h1>
    
    <!-- Dashboard Summary -->
    <div class="mt-6 grid grid-cols-2 gap-4 md:grid-cols-4">
      <div class="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
        <p class="text-sm font-semibold text-slate-500">Tổng số đơn</p>
        <p class="text-2xl font-black text-slate-900">{{ totalOrders }}</p>
      </div>
      <div class="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
        <p class="text-sm font-semibold text-slate-500">Đơn chờ xác nhận</p>
        <p class="text-2xl font-black text-amber-600">{{ pendingOrders }}</p>
      </div>
    </div>

    <!-- Filters -->
    <form class="my-5 grid gap-3 rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200 md:grid-cols-5" @submit.prevent="load">
      <input v-model="filters.search" class="rounded-xl border p-3 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500" placeholder="Mã đơn / khách">
      <select v-model="filters.status" class="rounded-xl border p-3 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500">
        <option value="">Mọi trạng thái</option>
        <option value="PENDING_CONFIRMATION">Chờ xác nhận</option>
        <option value="CONFIRMED">Đã xác nhận</option>
        <option value="SHIPPING">Đang giao</option>
        <option value="COMPLETED">Hoàn thành</option>
        <option value="CANCELLED">Đã hủy</option>
        <option value="REFUND_PENDING">Chờ hoàn tiền</option>
      </select>
      <input v-model="filters.date_from" type="date" class="rounded-xl border p-3 text-slate-600 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500" title="Từ ngày">
      <input v-model="filters.date_to" type="date" class="rounded-xl border p-3 text-slate-600 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500" title="Đến ngày">
      <button class="rounded-xl bg-slate-950 font-bold text-white transition-colors hover:bg-slate-800">Lọc</button>
    </form>

    <p v-if="loading" class="animate-pulse font-medium text-slate-500">Đang tải dữ liệu…</p>
    <p v-else-if="error" class="font-medium text-rose-700">{{ error }}</p>
    
    <div v-else class="overflow-x-auto rounded-2xl bg-white shadow-sm ring-1 ring-slate-200">
      <table class="w-full text-left text-sm">
        <thead class="bg-slate-50">
          <tr>
            <th class="p-4 font-semibold text-slate-700">Mã đơn hàng</th>
            <th class="p-4 font-semibold text-slate-700">Phương thức thanh toán</th>
            <th class="p-4 font-semibold text-slate-700">Trạng thái thanh toán</th>
            <th class="min-w-[200px] p-4 font-semibold text-slate-700">Đơn của Shop</th>
            <th class="p-4 font-semibold text-slate-700">Tổng tiền</th>
            <th class="p-4 font-semibold text-slate-700">Ngày đặt</th>
            <th class="p-4 font-semibold text-slate-700">Thao tác</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr v-for="order in orders" :key="order.id" class="transition-colors hover:bg-slate-50" :class="{'bg-rose-50/30': order.shop_orders.some(s => s.fulfillment_status === 'REFUND_PENDING')}">
            <td class="p-4 font-mono font-bold text-indigo-600">{{ order.order_code }}</td>
            <td class="p-4">{{ order.payment_method }}</td>
            <td class="p-4">
              <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold" :class="order.payment_status === 'PAID' ? 'bg-green-100 text-green-800' : 'bg-slate-100 text-slate-800'">
                {{ order.payment_status === 'PAID' ? 'Đã thanh toán' : order.payment_status }}
              </span>
            </td>
            <td class="p-4 space-y-2">
              <div v-for="shop in order.shop_orders" :key="shop.id" class="flex items-center gap-2 rounded-lg border border-slate-100 bg-white p-2 text-xs shadow-sm">
                <span class="max-w-[120px] truncate font-bold" :title="shop.shop_name">{{ shop.shop_name }}</span>
                <span class="inline-flex rounded-full px-2 py-0.5 font-medium whitespace-nowrap" :class="getStatusColor(shop.fulfillment_status)">
                  {{ translateStatus(shop.fulfillment_status) }}
                </span>
              </div>
            </td>
            <td class="p-4 font-bold text-slate-900">{{ formatCurrency(order.grand_total) }}</td>
            <td class="p-4 text-slate-600">{{ new Date(order.placed_at).toLocaleString('vi-VN') }}</td>
            <td class="p-4">
              <RouterLink :to="`/admin/orders/${order.id}`" class="rounded-lg bg-slate-100 px-3 py-1.5 font-semibold text-slate-700 transition hover:bg-slate-200">
                Chi tiết
              </RouterLink>
            </td>
          </tr>
          <tr v-if="orders.length === 0">
            <td colspan="7" class="p-8 text-center text-slate-500">Không tìm thấy đơn hàng nào</td>
          </tr>
        </tbody>
      </table>
      
      <div class="flex items-center justify-between border-t border-slate-100 p-4">
        <button class="rounded-lg border px-3 py-1.5 text-sm font-bold text-slate-400 opacity-50" disabled type="button">Trang trước</button>
        <span class="text-sm font-medium text-slate-500">Trang 1 / 1</span>
        <button class="rounded-lg border px-3 py-1.5 text-sm font-bold text-slate-400 opacity-50" disabled type="button">Trang tiếp</button>
      </div>
    </div>
  </main>
</template>
