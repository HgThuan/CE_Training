<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { formatCurrency } from '@/shared/lib/formatters'

import { afterSalesApi } from '../api'
import type { ReturnRequest } from '../types'
import InputDialog from '@/shared/components/InputDialog.vue'

const requests = ref<ReturnRequest[]>([])
const error = ref('')

const isDecideDialogOpen = ref(false)
const selectedReturn = ref<{ item: ReturnRequest; action: 'APPROVE' | 'REJECT' } | null>(null)

async function load(): Promise<void> {
  try {
    requests.value = (await afterSalesApi.sellerReturns()).data.data
  } catch {
    error.value = 'Không thể tải yêu cầu trả hàng.'
  }
}

function openDecideDialog(item: ReturnRequest, action: 'APPROVE' | 'REJECT') {
  selectedReturn.value = { item, action }
  isDecideDialogOpen.value = true
}

async function handleDecideConfirm(response: string) {
  if (!response.trim() || !selectedReturn.value) return
  isDecideDialogOpen.value = false

  await afterSalesApi.decideReturn(
    selectedReturn.value.item.id,
    selectedReturn.value.action,
    response,
  )
  selectedReturn.value = null
  await load()
}

onMounted(load)
</script>

<template>
  <main class="mx-auto max-w-5xl space-y-5 px-4 py-8">
    <div>
      <p class="font-bold text-indigo-600">CUS-18</p>
      <h1 class="text-3xl font-black">Yêu cầu trả hàng</h1>
    </div>
    <p v-if="error" class="text-rose-700">{{ error }}</p>
    <article v-for="item in requests" :key="item.id" class="rounded-2xl bg-white p-5 shadow-sm">
      <div class="flex justify-between">
        <div>
          <h2 class="font-black">{{ item.shop_order_code }}</h2>
          <p class="text-sm text-slate-500">{{ item.customer_email }}</p>
        </div>
        <b>{{ item.status }}</b>
      </div>
      <p class="my-4">{{ item.reason_detail }}</p>

      <!-- Media List from ReturnRequest (If available) -->
      <div v-if="item.media && item.media.length > 0" class="flex gap-2 mb-4">
        <div
          v-for="media in item.media"
          :key="media.id"
          class="h-16 w-16 overflow-hidden rounded-lg border"
        >
          <img
            v-if="media.media_type === 'IMAGE'"
            :src="media.file_url"
            class="h-full w-full object-cover"
          />
          <video
            v-else-if="media.media_type === 'VIDEO'"
            :src="media.file_url"
            class="h-full w-full object-cover"
          ></video>
        </div>
      </div>

      <p v-for="line in item.items" :key="line.id" class="flex justify-between border-t py-3">
        <span>{{ line.product_name }} × {{ line.quantity }}</span>
        <b>{{ formatCurrency(line.requested_refund_amount) }}</b>
      </p>

      <div v-if="item.status === 'REQUESTED'" class="mt-3 flex gap-2">
        <button
          class="rounded-xl bg-emerald-600 px-4 py-2 font-bold text-white hover:bg-emerald-700"
          @click="openDecideDialog(item, 'APPROVE')"
        >
          Chấp thuận
        </button>
        <button
          class="rounded-xl bg-rose-600 px-4 py-2 font-bold text-white hover:bg-rose-700"
          @click="openDecideDialog(item, 'REJECT')"
        >
          Từ chối
        </button>
      </div>
    </article>

    <InputDialog
      :is-open="isDecideDialogOpen"
      :title="selectedReturn?.action === 'APPROVE' ? 'Chấp thuận trả hàng' : 'Từ chối trả hàng'"
      :placeholder="
        selectedReturn?.action === 'APPROVE'
          ? 'Nhập ghi chú chấp thuận...'
          : 'Nhập lý do từ chối...'
      "
      :confirm-text="
        selectedReturn?.action === 'APPROVE' ? 'Xác nhận chấp thuận' : 'Xác nhận từ chối'
      "
      :multiline="true"
      @close="isDecideDialogOpen = false"
      @confirm="handleDecideConfirm"
    />
  </main>
</template>
