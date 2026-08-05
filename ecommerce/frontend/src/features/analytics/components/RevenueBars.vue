<script setup lang="ts">
import { computed } from 'vue'
import type { ChartPoint } from '../types'

const props = defineProps<{ points: ChartPoint[] }>()
const maximum = computed(() => Math.max(...props.points.map((item) => Number(item.revenue)), 1))
</script>

<template>
  <div class="flex h-56 items-end gap-2 overflow-x-auto rounded-2xl bg-slate-50 p-4" aria-label="Biểu đồ doanh thu">
    <div v-for="point in points" :key="point.date" class="group flex min-w-8 flex-1 flex-col items-center gap-2">
      <span class="text-[10px] font-semibold text-slate-500 opacity-0 group-hover:opacity-100">{{ Number(point.revenue).toLocaleString('vi-VN') }}</span>
      <div class="w-full rounded-t-lg bg-indigo-500" :style="{ height: `${Math.max(4, Number(point.revenue) * 150 / maximum)}px` }" />
      <span class="text-[10px] text-slate-500">{{ point.date.slice(5) }}</span>
    </div>
    <p v-if="!points.length" class="m-auto text-sm text-slate-500">Chưa có doanh thu trong kỳ.</p>
  </div>
</template>
