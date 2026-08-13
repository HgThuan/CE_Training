<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { promotionApi } from '../../api'
import type { UserVoucher, UserVoucherStatus } from '../../types'

const tabs: Array<{ status: UserVoucherStatus; label: string }> = [
  { status: 'saved', label: 'Có thể dùng' },
  { status: 'used', label: 'Đã dùng' },
  { status: 'expired', label: 'Hết hạn' },
]
const active = ref<UserVoucherStatus>('saved')
const vouchers = ref<UserVoucher[]>([])
const loading = ref(false)

async function load(status = active.value): Promise<void> {
  active.value = status
  loading.value = true
  try {
    vouchers.value = (await promotionApi.myVouchers(status)).data.data
  } finally {
    loading.value = false
  }
}

onMounted(() => void load())
</script>

<template>
  <main class="mx-auto min-h-[70vh] max-w-5xl px-4 py-10 sm:px-6">
    <h1 class="text-4xl font-black">Voucher của tôi</h1>
    <div class="mt-6 flex flex-wrap gap-2">
      <button
        v-for="tab in tabs"
        :key="tab.status"
        class="rounded-xl px-4 py-2 text-sm font-bold"
        :class="active === tab.status ? 'bg-indigo-600 text-white' : 'border bg-white'"
        @click="load(tab.status)"
      >
        {{ tab.label }}
      </button>
    </div>
    <div class="mt-7 space-y-3">
      <article
        v-for="item in vouchers"
        :key="item.id"
        class="rounded-2xl border bg-white p-5"
        :class="active !== 'saved' && 'opacity-60'"
      >
        <div class="flex justify-between gap-4">
          <div>
            <p class="text-xs font-black uppercase text-indigo-600">{{ item.campaign.code }}</p>
            <h2 class="mt-1 font-black">{{ item.campaign.name }}</h2>
            <p class="mt-1 text-sm text-slate-500">
              Hạn dùng {{ new Date(item.campaign.end_time).toLocaleString('vi-VN') }}
            </p>
          </div>
          <span class="text-sm font-bold">{{
            tabs.find((tab) => tab.status === active)?.label
          }}</span>
        </div>
      </article>
      <p
        v-if="!loading && !vouchers.length"
        class="rounded-2xl border border-dashed p-10 text-center text-slate-500"
      >
        Chưa có voucher trong mục này.
      </p>
    </div>
  </main>
</template>
