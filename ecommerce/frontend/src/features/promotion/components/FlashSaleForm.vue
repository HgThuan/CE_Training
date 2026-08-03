<script setup lang="ts">
import { reactive, ref, watch } from 'vue'

import type { FlashSale, FlashSaleItem, FlashSalePayload } from '../types'
import FlashSaleItemPicker from './FlashSaleItemPicker.vue'

const props = defineProps<{ flashSale?: FlashSale | null; saving?: boolean }>()
const emit = defineEmits<{ submit: [payload: FlashSalePayload]; cancel: [] }>()
const error = ref('')
function localDate(value: string): string {
  const d = new Date(value)
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
}
const form = reactive({
  name: '',
  start_time: localDate(new Date().toISOString()),
  end_time: localDate(new Date(Date.now() + 3600000).toISOString()),
  is_active: true,
  items: [] as FlashSaleItem[],
})
watch(
  () => props.flashSale,
  (sale) => {
    if (sale)
      Object.assign(form, {
        name: sale.name,
        start_time: localDate(sale.start_time),
        end_time: localDate(sale.end_time),
        is_active: sale.is_active,
        items: sale.items.map((item) => ({ ...item })),
      })
  },
  { immediate: true },
)
function submit(): void {
  error.value = ''
  if (!form.name.trim()) error.value = 'Tên Flash Sale là bắt buộc'
  else if (new Date(form.start_time) >= new Date(form.end_time))
    error.value = 'Thời điểm kết thúc phải sau thời điểm bắt đầu'
  else if (!form.items.length) error.value = 'Cần ít nhất một sản phẩm'
  else if (
    form.items.some((item) => !item.variant || Number(item.sale_price) < 0 || item.quota < 1)
  )
    error.value = 'Thông tin sản phẩm Flash Sale chưa hợp lệ'
  else if (
    form.items.some(
      (item) => item.available_stock !== undefined && item.quota > item.available_stock,
    )
  )
    error.value = 'Số lượng Flash Sale không được vượt quá tồn kho hiện có'
  else if (
    form.items.some(
      (item) =>
        item.original_price !== undefined && Number(item.sale_price) > Number(item.original_price),
    )
  )
    error.value = 'Giá Flash Sale không được cao hơn giá bán hiện tại'
  if (error.value) return
  emit('submit', {
    name: form.name.trim(),
    start_time: new Date(form.start_time).toISOString(),
    end_time: new Date(form.end_time).toISOString(),
    is_active: form.is_active,
    items: form.items.map((item) => ({
      variant: item.variant,
      sale_price: String(item.sale_price),
      quota: item.quota,
    })),
  })
}
</script>

<template>
  <form class="space-y-5" @submit.prevent="submit">
    <p v-if="error" class="rounded-xl bg-rose-50 px-3 py-2 text-sm font-bold text-rose-700">
      {{ error }}
    </p>
    <label class="block text-sm font-bold"
      >Tên chương trình<input v-model="form.name" class="mt-1 w-full rounded-xl border px-3 py-2"
    /></label>
    <div class="grid gap-4 sm:grid-cols-2">
      <label class="text-sm font-bold"
        >Bắt đầu<input
          v-model="form.start_time"
          type="datetime-local"
          class="mt-1 w-full rounded-xl border px-3 py-2" /></label
      ><label class="text-sm font-bold"
        >Kết thúc<input
          v-model="form.end_time"
          type="datetime-local"
          class="mt-1 w-full rounded-xl border px-3 py-2"
      /></label>
    </div>
    <label class="flex gap-2 text-sm font-bold"
      ><input v-model="form.is_active" type="checkbox" /> Hoạt động</label
    ><FlashSaleItemPicker :items="form.items" @update:items="form.items = $event" />
    <div class="flex justify-end gap-2 border-t pt-4">
      <button type="button" class="rounded-xl px-4 py-2 font-bold" @click="emit('cancel')">
        Hủy</button
      ><button
        type="submit"
        :disabled="saving"
        class="rounded-xl bg-indigo-600 px-5 py-2 font-bold text-white disabled:opacity-50"
      >
        {{ saving ? 'Đang lưu...' : 'Lưu Flash Sale' }}
      </button>
    </div>
  </form>
</template>
