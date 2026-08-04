<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { formatCurrency } from '@/shared/lib/formatters'
import { orderApi } from '../api'
import type { CommerceOrder } from '../types'
const route=useRoute(), order=ref<CommerceOrder|null>(null), error=ref('')
async function load(){try{order.value=(await orderApi.customerOrder(String(route.params.orderId))).data.data}catch{error.value='Không thể tải chi tiết đơn.'}}
async function cancel(shopId:string){if(!order.value||!confirm('Bạn muốn hủy phần đơn này?'))return;await orderApi.cancel(order.value.id,shopId);await load()}
async function reorder(){if(order.value){await orderApi.reorder(order.value.id);alert('Đã thêm lại các sản phẩm còn khả dụng vào giỏ.')}}
async function retryPayment(){if(!order.value)return;try{const response=await orderApi.initiatePayment(order.value.id);window.location.assign(response.data.data.payment_url)}catch{error.value='Không thể khởi tạo lại thanh toán VNPay.'}}
onMounted(load)
</script>
<template><main class="mx-auto max-w-5xl space-y-5 px-4 py-8"><p v-if="error" class="text-rose-700">{{ error }}</p><template v-if="order"><div class="flex items-center justify-between"><div><p class="text-sm font-bold text-indigo-600">{{ order.payment_method }} · {{ order.payment_status }}</p><h1 class="text-3xl font-black">{{ order.order_code }}</h1></div><div class="flex gap-2"><button v-if="order.payment_method==='VNPAY' && order.payment_status==='PENDING'" class="rounded-xl bg-indigo-600 px-4 py-2 font-bold text-white" @click="retryPayment">Thanh toán lại</button><button class="rounded-xl border px-4 py-2 font-bold" @click="reorder">Mua lại</button></div></div>
<article v-for="shop in order.shop_orders" :key="shop.id" class="rounded-2xl bg-white p-5 shadow-sm"><div class="flex justify-between"><h2 class="font-black">{{ shop.shop_name }}</h2><b>{{ shop.fulfillment_status }}</b></div><div class="my-4 divide-y"><p v-for="item in shop.items" :key="item.id" class="flex justify-between py-3"><span>{{ item.product_name }} × {{ item.quantity }}</span><b>{{ formatCurrency(item.line_total) }}</b></p></div><p class="text-right text-lg font-black">{{ formatCurrency(shop.total_amount) }}</p><button v-if="shop.fulfillment_status==='PENDING_CONFIRMATION'" class="mt-3 rounded-xl bg-rose-600 px-4 py-2 font-bold text-white" @click="cancel(shop.id)">Hủy phần đơn</button><ol class="mt-5 border-l-2 border-indigo-200 pl-5"><li v-for="history in shop.status_history" :key="history.id" class="mb-3"><b>{{ history.to_status }}</b><p class="text-sm text-slate-500">{{ new Date(history.created_at).toLocaleString('vi-VN') }}</p></li></ol></article></template></main></template>
