<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { formatCurrency } from '@/shared/lib/formatters'

import { afterSalesApi } from '../api'
import type { Dispute } from '../types'

const disputes = ref<Dispute[]>([])
const error = ref('')
async function load(): Promise<void> {
  try {
    disputes.value = (await afterSalesApi.adminDisputes()).data.data
  } catch {
    error.value = 'Không thể tải tranh chấp.'
  }
}
async function resolve(
  item: Dispute,
  decision: 'REFUND_FULL' | 'REFUND_PARTIAL' | 'REJECT',
): Promise<void> {
  const note = window.prompt('Ghi chú quyết định cuối cùng')
  if (!note) return
  const payload: Record<string, unknown> = { decision, note }
  if (decision === 'REFUND_PARTIAL') {
    const amount = Number(window.prompt('Số tiền hoàn'))
    if (!amount) return
    payload.refund_amount = amount
  }
  await afterSalesApi.resolveDispute(item.id, payload)
  await load()
}
async function startReview(item: Dispute): Promise<void> {
  await afterSalesApi.reviewDispute(item.id)
  await load()
}
onMounted(load)
</script>

<template>
  <main class="mx-auto max-w-6xl space-y-5 px-4 py-8">
    <div>
      <p class="font-bold text-indigo-600">ADM-18</p>
      <h1 class="text-3xl font-black">Xử lý tranh chấp</h1>
    </div>
    <p v-if="error" class="text-rose-700">{{ error }}</p>
    <article v-for="item in disputes" :key="item.id" class="rounded-2xl bg-white p-5 shadow-sm">
      <div class="flex justify-between">
        <div>
          <h2 class="font-black">{{ item.return_request.shop_order_code }}</h2>
          <p class="text-sm text-slate-500">
            {{ item.return_request.customer_email }} · {{ item.return_request.shop_name }}
          </p>
        </div>
        <b>{{ item.status }}</b>
      </div>
      <p class="my-4">{{ item.return_request.reason_detail }}</p>
      <div class="rounded-xl bg-slate-50 p-4">
        <p
          v-for="line in item.return_request.items"
          :key="line.id"
          class="flex justify-between py-1"
        >
          <span>{{ line.product_name }} × {{ line.quantity }}</span
          ><b>{{ formatCurrency(line.requested_refund_amount) }}</b>
        </p>
      </div>
      <div v-if="item.status !== 'RESOLVED'" class="mt-4 flex flex-wrap gap-2">
        <button
          v-if="item.status === 'OPEN'"
          class="rounded-xl border border-indigo-200 px-4 py-2 font-bold text-indigo-700"
          @click="startReview(item)"
        >
          Tiếp nhận xử lý
        </button>
        <button
          class="rounded-xl bg-emerald-600 px-4 py-2 font-bold text-white"
          @click="resolve(item, 'REFUND_FULL')"
        >
          Hoàn toàn bộ</button
        ><button
          class="rounded-xl bg-amber-500 px-4 py-2 font-bold text-white"
          @click="resolve(item, 'REFUND_PARTIAL')"
        >
          Hoàn một phần</button
        ><button
          class="rounded-xl bg-rose-600 px-4 py-2 font-bold text-white"
          @click="resolve(item, 'REJECT')"
        >
          Từ chối
        </button>
      </div>
    </article>
  </main>
</template>
