<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { orderApi } from '@/features/order/api'
import type { CommerceOrder } from '@/features/order/types'
import { formatCurrency } from '@/shared/lib/formatters'

const route = useRoute()
const order = ref<CommerceOrder | null>(null)
const error = ref('')

const labels: Record<string, string> = {
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
const label = (value: string) => labels[value] ?? value.replaceAll('_', ' ')

onMounted(async () => {
  try {
    order.value = (await orderApi.adminOrder(String(route.params.orderId))).data.data
  } catch {
    error.value = 'Không thể tải chi tiết đơn hàng.'
  }
})
</script>

<template>
  <main class="mx-auto max-w-5xl px-4 py-8 sm:px-6">
    <RouterLink class="font-bold text-indigo-700" to="/admin/orders"
      >← Quay lại danh sách</RouterLink
    >
    <p v-if="error" class="mt-6 rounded-xl bg-rose-50 p-4 text-rose-700">{{ error }}</p>
    <p v-else-if="!order" class="mt-12 text-center text-slate-500">Đang tải chi tiết đơn hàng…</p>
    <template v-else>
      <div class="mt-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 class="text-3xl font-black">{{ order.order_code }}</h1>
          <p class="mt-2 text-slate-600">
            Đặt lúc {{ new Date(order.placed_at).toLocaleString('vi-VN') }}
          </p>
        </div>
        <strong class="text-2xl">{{ formatCurrency(order.grand_total) }}</strong>
      </div>
      <section
        class="mt-6 grid gap-4 rounded-2xl bg-white p-5 ring-1 ring-slate-200 sm:grid-cols-2"
      >
        <div>
          <p class="text-sm text-slate-500">Phương thức thanh toán</p>
          <p class="mt-1 font-bold">{{ order.payment_method }}</p>
        </div>
        <div>
          <p class="text-sm text-slate-500">Trạng thái thanh toán</p>
          <p class="mt-1 font-bold">{{ label(order.payment_status) }}</p>
        </div>
      </section>
      <section class="mt-6 space-y-4">
        <article
          v-for="shop in order.shop_orders"
          :key="shop.id"
          class="rounded-2xl bg-white p-5 ring-1 ring-slate-200"
        >
          <div class="flex flex-wrap justify-between gap-3">
            <div>
              <h2 class="text-lg font-black">{{ shop.shop_name }}</h2>
              <p class="text-sm text-slate-500">{{ shop.shop_order_code }}</p>
            </div>
            <span class="font-bold text-indigo-700">{{ label(shop.fulfillment_status) }}</span>
          </div>
          <div class="mt-4 divide-y">
            <div
              v-for="item in shop.items"
              :key="item.id"
              class="flex justify-between gap-4 py-3 text-sm"
            >
              <span>{{ item.product_name }} · {{ item.variant_name }} × {{ item.quantity }}</span
              ><b>{{ formatCurrency(item.line_total) }}</b>
            </div>
          </div>
        </article>
      </section>
    </template>
  </main>
</template>
