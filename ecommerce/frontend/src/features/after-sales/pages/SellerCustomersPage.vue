<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { formatCurrency } from '@/shared/lib/formatters'

import { afterSalesApi } from '../api'
import type { SellerCustomer, SellerCustomerOrder } from '../types'

const customers = ref<SellerCustomer[]>([])
const orders = ref<SellerCustomerOrder[]>([])
const selected = ref<SellerCustomer | null>(null)
const search = ref('')
const error = ref('')

async function load(): Promise<void> {
  try {
    customers.value = (await afterSalesApi.sellerCustomers(search.value)).data.data
  } catch {
    error.value = 'Không thể tải danh sách khách hàng.'
  }
}

async function openCustomer(customer: SellerCustomer): Promise<void> {
  selected.value = customer
  orders.value = (await afterSalesApi.sellerCustomerOrders(customer.id)).data.data
}

onMounted(load)
</script>

<template>
  <main class="mx-auto max-w-6xl space-y-6 px-4 py-8">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <p class="font-bold text-indigo-600">SEL-13</p>
        <h1 class="text-3xl font-black">Khách hàng của shop</h1>
      </div>
      <form class="flex gap-2" @submit.prevent="load">
        <input
          v-model="search"
          class="rounded-xl border px-4 py-2"
          placeholder="Tên hoặc email"
        /><button class="rounded-xl bg-indigo-600 px-4 py-2 font-bold text-white">Tìm</button>
      </form>
    </div>
    <p v-if="error" class="text-rose-700">{{ error }}</p>
    <div class="overflow-hidden rounded-2xl bg-white shadow-sm">
      <table class="w-full text-left">
        <thead class="bg-slate-100 text-sm">
          <tr>
            <th class="p-4">Khách hàng</th>
            <th>Số đơn</th>
            <th>Tổng chi tiêu</th>
            <th>Lần gần nhất</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="customer in customers"
            :key="customer.id"
            class="cursor-pointer border-t hover:bg-indigo-50"
            @click="openCustomer(customer)"
          >
            <td class="p-4">
              <b>{{ customer.full_name || 'Chưa cập nhật tên' }}</b>
              <p class="text-sm text-slate-500">{{ customer.email }}</p>
            </td>
            <td>{{ customer.order_count }}</td>
            <td class="font-bold">{{ formatCurrency(customer.total_spent) }}</td>
            <td>{{ new Date(customer.last_order_at).toLocaleDateString('vi-VN') }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <section v-if="selected" class="rounded-2xl bg-white p-5 shadow-sm">
      <h2 class="text-xl font-black">Lịch sử mua của {{ selected.email }}</h2>
      <article
        v-for="order in orders"
        :key="order.id"
        class="mt-4 flex justify-between rounded-xl border p-4"
      >
        <div>
          <b>{{ order.shop_order_code }}</b>
          <p class="text-sm text-slate-500">{{ order.fulfillment_status }}</p>
        </div>
        <b>{{ formatCurrency(order.total_amount) }}</b>
      </article>
    </section>
  </main>
</template>
