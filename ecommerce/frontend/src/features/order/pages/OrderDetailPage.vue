<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { formatCurrency } from '@/shared/lib/formatters'
import { afterSalesApi } from '@/features/after-sales/api'
import ReviewFormDialog from '@/features/after-sales/components/ReviewFormDialog.vue'
import type { ReturnRequest, Review } from '@/features/after-sales/types'
import { orderApi } from '../api'
import type { CommerceOrder, OrderItem } from '../types'
const route = useRoute(),
  order = ref<CommerceOrder | null>(null),
  error = ref(''),
  returns = ref<ReturnRequest[]>([]),
  reviewItem = ref<OrderItem | null>(null)
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
function saveReview(review: Review): void {
  if (reviewItem.value) reviewItem.value.review = review
  error.value = ''
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
    <template v-if="order"
      ><div class="flex items-center justify-between">
        <div>
          <p class="text-sm font-bold text-indigo-600">
            {{ order.payment_method }} · {{ order.payment_status }}
          </p>
          <h1 class="text-3xl font-black">{{ order.order_code }}</h1>
        </div>
        <button class="rounded-xl border px-4 py-2 font-bold" @click="reorder">Mua lại</button>
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
            <div>
              <span>{{ item.product_name }} × {{ item.quantity }}</span>
              <p v-if="item.review" class="mt-1 text-sm text-amber-600">
                {{ '★'.repeat(item.review.rating) }}
                <span class="ml-1 text-slate-500">{{ item.review.status }}</span>
              </p>
            </div>
            <div class="flex items-center gap-3">
              <b>{{ formatCurrency(item.line_total) }}</b
              ><button
                v-if="shop.fulfillment_status === 'COMPLETED'"
                class="rounded-lg border border-amber-300 px-3 py-1 text-sm font-bold text-amber-700"
                @click="reviewItem = item"
              >
                {{ item.review ? 'Sửa đánh giá' : 'Đánh giá' }}
              </button>
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
      </section></template
    >
    <ReviewFormDialog
      :open="reviewItem !== null"
      :order-item-id="reviewItem?.id ?? ''"
      :product-name="reviewItem?.product_name ?? ''"
      :review="reviewItem?.review ?? null"
      @close="reviewItem = null"
      @saved="saveReview"
    />
  </main>
</template>
