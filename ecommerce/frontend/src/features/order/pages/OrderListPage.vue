<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { orderApi } from '../api'
import type { CommerceOrder } from '../types'
import { formatCurrency } from '@/shared/lib/formatters'

const orders = ref<CommerceOrder[]>([]), loading = ref(true), error = ref(''), status = ref('')
const tabs = ['', 'PENDING_CONFIRMATION', 'CONFIRMED', 'SHIPPING', 'COMPLETED', 'CANCELLED']
async function load() { loading.value = true; try { orders.value = (await orderApi.customerOrders(status.value || undefined)).data.data } catch { error.value = 'Không thể tải đơn hàng.' } finally { loading.value = false } }
onMounted(load)
</script>
<template><main class="mx-auto max-w-6xl px-4 py-8"><h1 class="text-3xl font-black">Đơn hàng của tôi</h1>
<div class="my-5 flex gap-2 overflow-auto"><button v-for="tab in tabs" :key="tab" class="rounded-full border px-4 py-2 text-sm font-bold" :class="status===tab?'bg-indigo-600 text-white':''" @click="status=tab;load()">{{ tab || 'Tất cả' }}</button></div>
<p v-if="loading">Đang tải…</p><p v-else-if="error" class="text-rose-700">{{ error }}</p><p v-else-if="!orders.length">Chưa có đơn hàng.</p>
<div v-else class="space-y-4"><RouterLink v-for="order in orders" :key="order.id" :to="`/account/orders/${order.id}`" class="block rounded-2xl bg-white p-5 shadow-sm"><div class="flex justify-between"><b>{{ order.order_code }}</b><span>{{ order.payment_method }} · {{ order.payment_status }}</span></div><p class="mt-2">{{ order.shop_orders.length }} shop · <b>{{ formatCurrency(order.grand_total) }}</b></p></RouterLink></div></main></template>
