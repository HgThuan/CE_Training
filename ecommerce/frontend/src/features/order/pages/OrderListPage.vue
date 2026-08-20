<script setup lang="ts">
import {
  ArrowPathIcon,
  ChevronRightIcon,
  ClipboardDocumentListIcon,
  ShoppingBagIcon,
  TruckIcon,
} from '@heroicons/vue/24/outline'
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { formatCurrency } from '@/shared/lib/formatters'

import { orderApi } from '../api'
import type { CommerceOrder } from '../types'

const orders = ref<CommerceOrder[]>([])
const loading = ref(true)
const error = ref('')
const status = ref('')

const tabs = [
  { value: '', label: 'Tất cả' },
  { value: 'PENDING_CONFIRMATION', label: 'Chờ xác nhận' },
  { value: 'CONFIRMED', label: 'Đã xác nhận' },
  { value: 'SHIPPING', label: 'Đang giao' },
  { value: 'COMPLETED', label: 'Hoàn thành' },
  { value: 'CANCELLED', label: 'Đã hủy' },
]

const fulfillmentLabels: Record<string, string> = {
  PENDING_CONFIRMATION: 'Chờ shop xác nhận',
  CONFIRMED: 'Shop đã xác nhận',
  PACKING: 'Đang đóng gói',
  SHIPPING: 'Đang giao hàng',
  DELIVERED: 'Đã giao hàng',
  COMPLETED: 'Hoàn thành',
  CANCELLED: 'Đã hủy',
  RETURN_REQUESTED: 'Đang yêu cầu trả hàng',
  REFUND_PENDING: 'Đang chờ hoàn tiền',
  REFUNDED: 'Đã hoàn tiền',
}

const paymentLabels: Record<string, string> = {
  COD: 'Thanh toán khi nhận hàng',
  VNPAY: 'VNPay',
  PENDING: 'Chờ thanh toán',
  PAID: 'Đã thanh toán',
  FAILED: 'Thanh toán thất bại',
  REFUNDED: 'Đã hoàn tiền',
}

function labelFor(value: string, labels: Record<string, string>): string {
  return labels[value] ?? value.replaceAll('_', ' ').toLocaleLowerCase('vi-VN')
}

function statusClass(value: string): string {
  if (['COMPLETED', 'DELIVERED', 'PAID', 'REFUNDED'].includes(value)) {
    return 'bg-emerald-50 text-emerald-700'
  }
  if (['CANCELLED', 'FAILED'].includes(value)) return 'bg-rose-50 text-rose-700'
  if (value.includes('SHIPPING') || value.includes('PACKING')) return 'bg-sky-50 text-sky-700'
  return 'bg-amber-50 text-amber-800'
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('vi-VN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    orders.value = (await orderApi.customerOrders(status.value || undefined)).data.data
  } catch {
    error.value = 'Chưa thể tải đơn hàng. Vui lòng kiểm tra kết nối và thử lại.'
  } finally {
    loading.value = false
  }
}

async function selectStatus(value: string): Promise<void> {
  if (status.value === value && orders.value.length) return
  status.value = value
  await load()
}

onMounted(load)
</script>

<template>
  <main class="account-page" :aria-busy="loading">
    <header class="app-page-header">
      <div>
        <p class="app-page-eyebrow">Tài khoản · Đơn mua</p>
        <h1 class="app-page-title">Đơn hàng của tôi</h1>
        <p class="app-page-description">
          Theo dõi từng kiện hàng, thanh toán, đổi trả và liên hệ gian hàng tại một nơi.
        </p>
      </div>
      <RouterLink class="account-page__secondary-action" to="/products">
        <ShoppingBagIcon class="h-5 w-5" aria-hidden="true" />
        Tiếp tục mua sắm
      </RouterLink>
    </header>

    <nav class="account-filter-tabs" aria-label="Lọc đơn hàng theo trạng thái">
      <button
        v-for="tab in tabs"
        :key="tab.value || 'all'"
        type="button"
        :class="{ 'account-filter-tabs__button--active': status === tab.value }"
        class="account-filter-tabs__button"
        :aria-pressed="status === tab.value"
        @click="selectStatus(tab.value)"
      >
        {{ tab.label }}
      </button>
    </nav>

    <section v-if="loading" class="space-y-3" aria-label="Đang tải đơn hàng">
      <div v-for="index in 3" :key="index" class="h-36 animate-pulse rounded-2xl bg-white/70" />
    </section>

    <section v-else-if="error" class="account-state account-state--error" role="alert">
      <ArrowPathIcon class="h-8 w-8" aria-hidden="true" />
      <div>
        <h2>Không thể tải đơn hàng</h2>
        <p>{{ error }}</p>
      </div>
      <button type="button" @click="load">Thử lại</button>
    </section>

    <section v-else-if="!orders.length" class="account-state">
      <ClipboardDocumentListIcon class="h-10 w-10" aria-hidden="true" />
      <h2>Chưa có đơn hàng ở trạng thái này</h2>
      <p>Khám phá sản phẩm phù hợp hoặc chọn trạng thái khác để xem lại đơn cũ.</p>
      <RouterLink to="/products">Khám phá sản phẩm</RouterLink>
    </section>

    <section v-else class="space-y-4" aria-live="polite">
      <RouterLink
        v-for="order in orders"
        :key="order.id"
        :to="`/account/orders/${order.id}`"
        class="order-summary-card"
      >
        <div class="order-summary-card__header">
          <div>
            <p class="order-summary-card__code">{{ order.order_code }}</p>
            <p class="order-summary-card__date">Đặt lúc {{ formatDate(order.placed_at) }}</p>
          </div>
          <span class="app-status" :class="statusClass(order.payment_status)">
            {{ labelFor(order.payment_status, paymentLabels) }}
          </span>
        </div>

        <div class="order-summary-card__shops">
          <div v-for="shop in order.shop_orders" :key="shop.id">
            <span class="order-summary-card__shop-name">{{ shop.shop_name }}</span>
            <span class="app-status" :class="statusClass(shop.fulfillment_status)">
              <TruckIcon class="h-3.5 w-3.5" aria-hidden="true" />
              {{ labelFor(shop.fulfillment_status, fulfillmentLabels) }}
            </span>
          </div>
        </div>

        <div class="order-summary-card__footer">
          <p>
            {{ order.shop_orders.length }} gian hàng ·
            {{ labelFor(order.payment_method, paymentLabels) }}
          </p>
          <strong>{{ formatCurrency(order.grand_total) }}</strong>
          <span class="order-summary-card__detail">
            Xem chi tiết <ChevronRightIcon class="h-4 w-4" aria-hidden="true" />
          </span>
        </div>
      </RouterLink>
    </section>
  </main>
</template>
