<script setup lang="ts">
import type { FlashSaleItem } from '../types'

const props = defineProps<{ items: FlashSaleItem[] }>()
const emit = defineEmits<{ 'update:items': [items: FlashSaleItem[]] }>()

function add(): void {
  emit('update:items', [...props.items, { variant: '', sale_price: '0', quota: 1, sold_count: 0 }])
}

function update(
  index: number,
  field: 'variant' | 'sale_price' | 'quota',
  value: string | number,
): void {
  const items = props.items.map((item, position) =>
    position === index ? { ...item, [field]: value } : item,
  )
  emit('update:items', items)
}

function remove(index: number): void {
  emit(
    'update:items',
    props.items.filter((_, position) => position !== index),
  )
}
</script>

<template>
  <fieldset class="space-y-3">
    <legend class="text-sm font-black">Sản phẩm tham gia</legend>
    <div
      v-for="(item, index) in items"
      :key="item.id ?? index"
      class="grid gap-3 rounded-2xl bg-slate-50 p-4 sm:grid-cols-[1fr_150px_110px_auto]"
    >
      <label class="text-xs font-bold"
        >Variant UUID<input
          :value="item.variant"
          class="mt-1 w-full rounded-xl border px-3 py-2 font-mono"
          :disabled="item.sold_count > 0"
          @input="update(index, 'variant', ($event.target as HTMLInputElement).value)"
      /></label>
      <label class="text-xs font-bold"
        >Giá sale<input
          :value="item.sale_price"
          type="number"
          min="0"
          class="mt-1 w-full rounded-xl border px-3 py-2"
          :disabled="item.sold_count > 0"
          @input="update(index, 'sale_price', ($event.target as HTMLInputElement).value)"
      /></label>
      <label class="text-xs font-bold"
        >Quota<input
          :value="item.quota"
          type="number"
          min="1"
          class="mt-1 w-full rounded-xl border px-3 py-2"
          :disabled="item.sold_count > 0"
          @input="update(index, 'quota', Number(($event.target as HTMLInputElement).value))"
      /></label>
      <button
        type="button"
        class="self-end rounded-xl px-3 py-2 font-bold text-rose-700 disabled:opacity-40"
        :disabled="item.sold_count > 0"
        @click="remove(index)"
      >
        Xóa
      </button>
      <p v-if="item.sold_count > 0" class="text-xs text-amber-700 sm:col-span-4">
        Đã bán {{ item.sold_count }} sản phẩm; giá và quota được khóa trên giao diện.
      </p>
    </div>
    <button
      type="button"
      class="rounded-xl border border-indigo-300 px-4 py-2 text-sm font-bold text-indigo-700"
      @click="add"
    >
      + Thêm variant
    </button>
  </fieldset>
</template>
