<script setup lang="ts">
import { HandThumbDownIcon, HandThumbUpIcon, SparklesIcon } from '@heroicons/vue/24/outline'
import { onBeforeUnmount, ref, watch } from 'vue'

import { productApi } from '../api'
import type { ProductAIReviewSummary as ProductAIReviewSummaryData } from '../types'

const props = defineProps<{ productId: string }>()
const summary = ref<ProductAIReviewSummaryData | null>(null)
const loading = ref(false)
let requestSequence = 0

async function loadSummary(): Promise<void> {
  const sequence = ++requestSequence
  loading.value = true
  summary.value = null
  try {
    const response = await productApi.aiReviewSummary(props.productId)
    if (sequence === requestSequence) summary.value = response.data.data
  } catch {
    if (sequence === requestSequence) summary.value = null
  } finally {
    if (sequence === requestSequence) loading.value = false
  }
}

watch(() => props.productId, loadSummary, { immediate: true })

onBeforeUnmount(() => {
  requestSequence += 1
})
</script>

<template>
  <div
    v-if="loading"
    class="mb-8 space-y-3 border-b border-slate-200 pb-8"
    role="status"
    aria-label="Đang tải tóm tắt đánh giá"
  >
    <div class="h-6 w-48 animate-pulse rounded bg-slate-200" />
    <div class="h-4 w-full animate-pulse rounded bg-slate-100" />
    <div class="h-4 w-3/4 animate-pulse rounded bg-slate-100" />
  </div>

  <section v-else-if="summary" class="mb-8 border-b border-slate-200 pb-8">
    <div class="flex flex-wrap items-center gap-3">
      <h2 class="text-xl font-black text-slate-950">Tổng quan đánh giá</h2>
      <span
        v-if="summary.is_ai_generated"
        class="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-bold text-indigo-700"
      >
        <SparklesIcon class="h-4 w-4" aria-hidden="true" />
        {{ summary.ai_label || 'Tạo bởi AI' }}
      </span>
      <span class="text-xs font-semibold text-slate-500">
        Dựa trên {{ summary.sample_count }} đánh giá
      </span>
    </div>

    <p class="mt-4 max-w-3xl [overflow-wrap:anywhere] leading-7 text-slate-700">
      {{ summary.summary }}
    </p>

    <div v-if="summary.pros.length || summary.cons.length" class="mt-6 grid gap-6 sm:grid-cols-2">
      <div v-if="summary.pros.length">
        <h3 class="flex items-center gap-2 text-sm font-black text-emerald-800">
          <HandThumbUpIcon class="h-5 w-5" aria-hidden="true" /> Điểm được yêu thích
        </h3>
        <ul class="mt-3 space-y-2 text-sm leading-6 text-slate-700">
          <li
            v-for="(pro, index) in summary.pros"
            :key="`${index}-${pro}`"
            class="[overflow-wrap:anywhere]"
          >
            {{ pro }}
          </li>
        </ul>
      </div>
      <div v-if="summary.cons.length">
        <h3 class="flex items-center gap-2 text-sm font-black text-rose-800">
          <HandThumbDownIcon class="h-5 w-5" aria-hidden="true" /> Điểm cần cân nhắc
        </h3>
        <ul class="mt-3 space-y-2 text-sm leading-6 text-slate-700">
          <li
            v-for="(con, index) in summary.cons"
            :key="`${index}-${con}`"
            class="[overflow-wrap:anywhere]"
          >
            {{ con }}
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>
