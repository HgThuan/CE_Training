<script setup lang="ts">
import { SparklesIcon } from '@heroicons/vue/24/solid'

import type { ProductCompareData } from '../types'

defineProps<{ comparison: ProductCompareData }>()
</script>

<template>
  <section class="mt-6 overflow-hidden rounded-3xl bg-white shadow-sm ring-1 ring-slate-200">
    <div class="flex flex-wrap items-start justify-between gap-3 px-5 py-5 sm:px-6">
      <div>
        <h2 class="text-xl font-black text-slate-950">Bảng so sánh</h2>
        <p class="mt-1 text-sm leading-6 text-slate-600">
          Đối chiếu các thông tin quan trọng trước khi chọn mua.
        </p>
      </div>
      <span
        v-if="comparison.is_ai_generated"
        class="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1.5 text-xs font-bold text-indigo-700"
      >
        <SparklesIcon class="h-4 w-4" />
        {{ comparison.ai_label }}
      </span>
    </div>
    <div class="overflow-x-auto border-t border-slate-200">
      <table class="w-full min-w-[720px] border-collapse text-left text-sm">
        <thead class="bg-slate-50 text-slate-950">
          <tr>
            <th class="sticky left-0 z-10 w-44 bg-slate-50 px-5 py-4 font-black">Tiêu chí</th>
            <th
              v-for="product in comparison.products"
              :key="product.id"
              class="min-w-48 px-5 py-4 font-black"
            >
              {{ product.name }}
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr
            v-for="(row, rowIndex) in comparison.rows"
            :key="`${row.label}-${rowIndex}`"
            class="align-top"
          >
            <th class="sticky left-0 bg-white px-5 py-4 font-bold text-slate-700">
              {{ row.label }}
            </th>
            <td
              v-for="(value, index) in row.values"
              :key="`${row.label}-${comparison.products[index]?.id ?? index}`"
              class="whitespace-pre-line px-5 py-4 leading-6 text-slate-700"
            >
              {{ value || '—' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div
      v-if="comparison.recommendations.length"
      class="border-t border-slate-200 bg-slate-50 px-5 py-5 sm:px-6"
    >
      <h3 class="font-black text-slate-950">Gợi ý theo nhu cầu</h3>
      <ul class="mt-3 grid gap-3 sm:grid-cols-2">
        <li
          v-for="recommendation in comparison.recommendations"
          :key="`${recommendation.need}-${recommendation.product_index}`"
          class="rounded-2xl bg-white p-4 ring-1 ring-slate-200"
        >
          <p class="font-bold text-indigo-700">{{ recommendation.need }}</p>
          <p class="mt-1 text-sm leading-6 text-slate-700">
            <strong>{{ comparison.products[recommendation.product_index]?.name }}:</strong>
            {{ recommendation.reason }}
          </p>
        </li>
      </ul>
    </div>
  </section>
</template>
