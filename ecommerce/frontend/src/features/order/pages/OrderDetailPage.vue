<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { formatCurrency } from '@/shared/lib/formatters'
import { afterSalesApi } from '@/features/after-sales/api'
import type { ReturnRequest } from '@/features/after-sales/types'
import { orderApi } from '../api'
import type { CommerceOrder, OrderItem } from '../types'
import ReviewDialog from '@/features/after-sales/components/ReviewDialog.vue'

const route = useRoute(),
  order = ref<CommerceOrder | null>(null),
  error = ref(''),
  returns = ref<ReturnRequest[]>([])

const isReviewDialogOpen = ref(false)
const selectedOrderItem = ref<OrderItem | null>(null)

async function load() {
  try {
    const orderId = String(route.params.orderId)
    order.value = (await orderApi.customerOrder(orderId)).data.data
    returns.value = (await afterSalesApi.orderReturns(orderId)).data.data
  } catch {
    error.value = 'Không thể tải chi tiết đơn.'
  }
}
async function cancel(shopId: string) {
  if (!order.value || !confirm('Bạn muốn hủy phần đơn này?')) return
  await orderApi.cancel(order.value.id, shopId)
  await load()
}
async function reorder() {
  if (order.value) {
    await orderApi.reorder(order.value.id)
    alert('Đã thêm lại các sản phẩm còn khả dụng vào giỏ.')
  }
}
async function retryPayment() {
  if (!order.value) return
  try {
    const response = await orderApi.initiatePayment(order.value.id)
    window.location.assign(response.data.data.payment_url)
  } catch {
    error.value = 'Không thể khởi tạo lại thanh toán VNPay.'
  }
}

function openReviewDialog(item: OrderItem) {
  selectedOrderItem.value = item
  isReviewDialogOpen.value = true
}

function isReviewExpired(editableUntil: string | null) {
  if (!editableUntil) return false
  return new Date(editableUntil) < new Date()
}

function renderStars(rating: number) {
  return '★'.repeat(rating) + '☆'.repeat(5 - rating)
}

function formatDateShort(dateString: string) {
  const date = new Date(dateString)
  return `${date.getDate().toString().padStart(2, '0')}/${(date.getMonth() + 1).toString().padStart(2, '0')}`
}

async function createReturn(shop: CommerceOrder['shop_orders'][number]) {
  if (!order.value) return
  const reason = prompt('Mô tả lý do trả hàng / hoàn tiền')
  if (!reason) return
  const image = prompt('URL ảnh chứng cứ') ?? ''
  try {
    await afterSalesApi.createReturn(order.value.id, {
      shop_order_id: shop.id,
      reason_code: 'OTHER',
      reason_detail: reason,
      items: shop.items.map((item) => ({ order_item_id: item.id, quantity: item.quantity })),
      media: image ? [{ media_type: 'IMAGE', file_url: image }] : [],
    })
    await load()
  } catch {
    error.value = 'Không thể tạo yêu cầu trả hàng.'
  }
}
async function escalate(item: ReturnRequest) {
  if (!confirm('Chuyển khiếu nại này đến Admin?')) return
  await afterSalesApi.escalateReturn(item.id)
  await load()
}
onMounted(load)
</script>
<template>
  <main class="mx-auto max-w-5xl space-y-5 px-4 py-8">
    <p v-if="error" class="text-rose-700">{{ error }}</p>
    <template v-if="order">
      <div class="flex items-center justify-between">
        <div>
          <p class="text-sm font-bold text-indigo-600">
            {{ order.payment_method }} · {{ order.payment_status }}
          </p>
          <h1 class="text-3xl font-black">{{ order.order_code }}</h1>
        </div>
        <div class="flex gap-2">
          <button v-if="order.payment_method === 'VNPAY' && order.payment_status === 'PENDING'" class="rounded-xl bg-indigo-600 px-4 py-2 font-bold text-white" @click="retryPayment">Thanh toán lại</button>
          <button class="rounded-xl border px-4 py-2 font-bold" @click="reorder">Mua lại</button>
        </div>
      </div>
      <article
        v-for="shop in order.shop_orders"
        :key="shop.id"
        class="rounded-2xl bg-white p-5 shadow-sm"
      >
        <div class="flex justify-between">
          <h2 class="font-black">{{ shop.shop_name }}</h2>
          <b>{{ shop.fulfillment_status }}</b>
        </div>
        <div class="my-4 divide-y">
          <div
            v-for="item in shop.items"
            :key="item.id"
            class="flex items-center justify-between gap-3 py-3"
          >
            <span>{{ item.product_name }} × {{ item.quantity }}</span>
            <div class="flex items-center gap-3">
              <b>{{ formatCurrency(item.line_total) }}</b>
              <template v-if="shop.fulfillment_status === 'COMPLETED'">
                <!-- Chưa đánh giá -->
                <button
                  v-if="!item.review"
                  class="rounded-lg border border-amber-300 px-3 py-1 text-sm font-bold text-amber-700 hover:bg-amber-50"
                  @click="openReviewDialog(item)"
                >
                  Đánh giá
                </button>
                <!-- Đã đánh giá, còn hạn sửa -->
                <button
                  v-else-if="!isReviewExpired(item.review.editable_until)"
                  class="rounded-lg border border-amber-300 bg-amber-50 px-3 py-1 text-sm font-medium text-amber-800 hover:bg-amber-100 flex items-center gap-1"
                  @click="openReviewDialog(item)"
                >
                  <span class="text-amber-500 tracking-widest text-xs">{{ renderStars(item.review.rating) }}</span>
                  <span class="mx-1">·</span>
                  Sửa đến {{ formatDateShort(item.review.editable_until!) }}
                </button>
                <!-- Đã đánh giá, hết hạn sửa -->
                <button
                  v-else
                  class="rounded-lg border border-gray-200 bg-gray-50 px-3 py-1 text-sm font-medium text-gray-500 cursor-not-allowed flex items-center gap-1"
                  disabled
                >
                  <span class="text-gray-400 tracking-widest text-xs">{{ renderStars(item.review.rating) }}</span>
                </button>
              </template>
            </div>
          </div>
        </div>
        <p class="text-right text-lg font-black">{{ formatCurrency(shop.total_amount) }}</p>
        <div class="mt-3 flex gap-2">
          <RouterLink
            class="rounded-xl border border-indigo-300 px-4 py-2 font-bold text-indigo-700"
            :to="{ name: 'customer-chat', query: { shop: shop.shop_slug, order: shop.id } }"
          >
            Chat với shop
          </RouterLink>
          <button
            v-if="shop.fulfillment_status === 'PENDING_CONFIRMATION'"
            class="rounded-xl bg-rose-600 px-4 py-2 font-bold text-white"
            @click="cancel(shop.id)"
          >
            Hủy phần đơn</button
          ><button
            v-if="shop.fulfillment_status === 'COMPLETED'"
            class="rounded-xl bg-indigo-600 px-4 py-2 font-bold text-white"
            @click="createReturn(shop)"
          >
            Trả hàng / hoàn tiền
          </button>
        </div>
        <ol class="mt-5 border-l-2 border-indigo-200 pl-5">
          <li v-for="history in shop.status_history" :key="history.id" class="mb-3">
            <b>{{ history.to_status }}</b>
            <p class="text-sm text-slate-500">
              {{ new Date(history.created_at).toLocaleString('vi-VN') }}
            </p>
          </li>
        </ol>
      </article>
      <section v-if="returns.length" class="space-y-3">
        <h2 class="text-xl font-black">Yêu cầu trả hàng</h2>
        <article v-for="item in returns" :key="item.id" class="rounded-2xl border bg-white p-5">
          <div class="flex justify-between">
            <b>{{ item.shop_order_code }}</b
            ><b>{{ item.status }}</b>
          </div>
          <p class="mt-2">{{ item.reason_detail }}</p>
          <p v-if="item.seller_response" class="mt-2 rounded-xl bg-slate-100 p-3">
            Seller: {{ item.seller_response }}
          </p>
          <button
            v-if="item.status === 'SELLER_REJECTED'"
            class="mt-3 rounded-xl bg-rose-600 px-4 py-2 font-bold text-white"
            @click="escalate(item)"
          >
            Khiếu nại đến Admin
          </button>
        </article>
      </section>
    </template>
    
    <ReviewDialog 
      :is-open="isReviewDialogOpen" 
      :order-item="selectedOrderItem" 
      @close="isReviewDialogOpen = false" 
      @submitted="load" 
    />
  </main>
</template>
