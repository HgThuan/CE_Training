<script setup lang="ts">
import type { SearchSort } from '../types'

defineProps<{ modelValue: SearchSort | '' }>()

const emit = defineEmits<{
  'update:modelValue': [value: SearchSort | '']
}>()

function updateSort(event: Event): void {
  emit('update:modelValue', (event.target as HTMLSelectElement).value as SearchSort | '')
}
</script>

<template>
  <label class="flex items-center gap-3 text-sm font-semibold">
    <span class="hidden text-slate-500 sm:inline">Sắp xếp</span>
    <select
      class="rounded-xl border border-slate-300 bg-white px-3 py-2.5"
      :value="modelValue"
      aria-label="Sắp xếp kết quả"
      @change="updateSort"
    >
      <option value="">Liên quan nhất</option>
      <option value="-created_at">Mới nhất</option>
      <option value="price">Giá thấp đến cao</option>
      <option value="-price">Giá cao đến thấp</option>
      <option value="-sold_count">Bán chạy</option>
      <option value="-avg_rating">Đánh giá tốt</option>
    </select>
  </label>
</template>
