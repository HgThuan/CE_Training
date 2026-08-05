<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { afterSalesApi } from '../api'
import type { ReviewReport } from '../types'

const reports = ref<ReviewReport[]>([])
async function load(): Promise<void> {
  reports.value = (await afterSalesApi.reviewReports()).data.data
}
async function resolve(item: ReviewReport, action: 'HIDE' | 'KEEP'): Promise<void> {
  const note = window.prompt('Ghi chú xử lý') ?? ''
  await afterSalesApi.resolveReviewReport(item.id, action, note)
  await load()
}
onMounted(load)
</script>

<template>
  <main class="mx-auto max-w-5xl space-y-5 px-4 py-8">
    <div>
      <p class="font-bold text-indigo-600">SEL-15</p>
      <h1 class="text-3xl font-black">Báo cáo đánh giá</h1>
    </div>
    <article v-for="item in reports" :key="item.id" class="rounded-2xl bg-white p-5 shadow-sm">
      <div class="flex justify-between">
        <h2 class="font-black">{{ item.review.product_name }}</h2>
        <b>{{ item.reason_code }}</b>
      </div>
      <p class="my-3">{{ item.review.content }}</p>
      <p class="rounded-xl bg-rose-50 p-3 text-rose-800">{{ item.reason_detail }}</p>
      <div class="mt-4 flex gap-2">
        <button
          class="rounded-xl bg-rose-600 px-4 py-2 font-bold text-white"
          @click="resolve(item, 'HIDE')"
        >
          Ẩn review</button
        ><button class="rounded-xl border px-4 py-2 font-bold" @click="resolve(item, 'KEEP')">
          Giữ review
        </button>
      </div>
    </article>
  </main>
</template>
