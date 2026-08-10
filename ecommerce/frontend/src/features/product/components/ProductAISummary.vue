<script setup lang="ts">
import { CheckCircleIcon, SparklesIcon } from '@heroicons/vue/24/outline'
import { onBeforeUnmount, ref, watch } from 'vue'

import { productApi } from '../api'
import type { ProductAISummary as ProductAISummaryData } from '../types'

const props = defineProps<{ productId: string }>()
const summary = ref<ProductAISummaryData | null>(null)
const loading = ref(false)
let requestSequence = 0

async function loadSummary(): Promise<void> {
  const sequence = ++requestSequence
  loading.value = true
  summary.value = null
  try {
    const response = await productApi.aiSummary(props.productId)
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
    aria-label="Đang tải tóm tắt sản phẩm"
  >
    <div class="h-6 w-40 animate-pulse rounded bg-slate-200" />
    <div class="h-4 w-full animate-pulse rounded bg-slate-100" />
    <div class="h-4 w-4/5 animate-pulse rounded bg-slate-100" />
  </div>

  <section v-else-if="summary?.summary" class="mb-8 border-b border-slate-200 pb-8">
    <div class="flex flex-wrap items-center gap-3">
      <h2 class="text-xl font-black text-slate-950">Tóm tắt nhanh</h2>
      <span
        v-if="summary.is_ai_generated"
        class="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-bold text-indigo-700"
      >
        <SparklesIcon class="h-4 w-4" aria-hidden="true" />
        {{ summary.ai_label || 'Tạo bởi AI' }}
      </span>
    </div>

    <p class="mt-4 max-w-3xl [overflow-wrap:anywhere] leading-7 text-slate-700">
      {{ summary.summary }}
    </p>

    <ul v-if="summary.highlights.length" class="mt-5 grid gap-3 sm:grid-cols-2">
      <li
        v-for="(highlight, index) in summary.highlights"
        :key="`${index}-${highlight}`"
        class="flex min-w-0 items-start gap-2 text-sm leading-6 text-slate-700"
      >
        <CheckCircleIcon class="mt-0.5 h-5 w-5 shrink-0 text-emerald-600" aria-hidden="true" />
        <span class="[overflow-wrap:anywhere]">{{ highlight }}</span>
      </li>
    </ul>

    <p v-if="summary.target_audience" class="mt-5 text-sm leading-6 text-slate-600">
      <strong class="text-slate-900">Phù hợp với:</strong> {{ summary.target_audience }}
    </p>

    <dl
      v-if="Object.keys(summary.key_specs).length"
      class="mt-5 grid gap-x-8 gap-y-3 sm:grid-cols-2"
    >
      <div v-for="(value, key) in summary.key_specs" :key="key" class="min-w-0 text-sm">
        <dt class="font-bold text-slate-900">{{ key }}</dt>
        <dd class="mt-1 [overflow-wrap:anywhere] text-slate-600">{{ value }}</dd>
      </div>
    </dl>
  </section>
</template>
