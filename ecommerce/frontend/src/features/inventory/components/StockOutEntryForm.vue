<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'

import type { InventoryBalance, StockOutEntry, StockOutEntryPayload } from '../types'

const props = defineProps<{
  inventory: InventoryBalance[]
  entry?: StockOutEntry | null
  submitting?: boolean
}>()
const emit = defineEmits<{
  submit: [payload: StockOutEntryPayload]
  cancel: []
}>()

const errorMessage = ref('')
const form = reactive<StockOutEntryPayload>({
  entry_type: 'out',
  reason: '',
  items: [{ variant_id: '', quantity: 1 }],
})
const disabled = computed(() => props.entry?.status === 'confirmed' || props.submitting)

watch(
  () => props.entry,
  (entry) => {
    form.entry_type = entry?.entry_type ?? 'out'
    form.reason = entry?.reason ?? ''
    form.items = entry?.items.length
      ? entry.items.map((item) => ({
          variant_id: item.variant_id,
          quantity: item.quantity,
        }))
      : [{ variant_id: '', quantity: 1 }]
    errorMessage.value = ''
  },
  { immediate: true },
)

function addItem(): void {
  form.items.push({ variant_id: '', quantity: form.entry_type === 'out' ? 1 : 0 })
}

function removeItem(index: number): void {
  if (form.items.length > 1) form.items.splice(index, 1)
}

function submit(): void {
  errorMessage.value = ''
  if (!form.reason.trim()) {
    errorMessage.value = 'Lý do xuất/kiểm kê là bắt buộc.'
    return
  }
  if (
    form.items.some(
      (item) =>
        !item.variant_id ||
        !Number.isInteger(Number(item.quantity)) ||
        Number(item.quantity) < 0 ||
        (form.entry_type === 'out' && Number(item.quantity) === 0),
    )
  ) {
    errorMessage.value =
      form.entry_type === 'out'
        ? 'Mỗi dòng xuất cần biến thể và số lượng nguyên dương.'
        : 'Tồn thực tế phải là số nguyên không âm.'
    return
  }
  if (new Set(form.items.map((item) => item.variant_id)).size !== form.items.length) {
    errorMessage.value = 'Một biến thể chỉ được xuất hiện một lần.'
    return
  }
  emit('submit', {
    entry_type: form.entry_type,
    reason: form.reason.trim(),
    items: form.items.map((item) => ({
      variant_id: item.variant_id,
      quantity: Number(item.quantity),
    })),
  })
}
</script>

<template>
  <form class="space-y-5" @submit.prevent="submit">
    <p v-if="errorMessage" class="rounded-xl bg-rose-50 p-3 text-rose-700" role="alert">
      {{ errorMessage }}
    </p>
    <div class="grid gap-4 md:grid-cols-2">
      <label class="block">
        <span class="mb-1.5 block text-sm font-bold text-slate-700">Loại phiếu</span>
        <select
          v-model="form.entry_type"
          class="w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5"
          :disabled="disabled"
        >
          <option value="out">Xuất kho</option>
          <option value="adjustment">Kiểm kê / điều chỉnh</option>
        </select>
      </label>
      <label class="block">
        <span class="mb-1.5 block text-sm font-bold text-slate-700">Lý do</span>
        <input
          v-model.trim="form.reason"
          class="w-full rounded-xl border border-slate-300 px-3 py-2.5"
          :disabled="disabled"
          required
        />
      </label>
    </div>
    <p class="text-sm text-slate-600">
      Với kiểm kê, số lượng là tồn thực tế mới. Với xuất kho, số lượng là phần cần trừ.
    </p>
    <div class="space-y-3">
      <div
        v-for="(item, index) in form.items"
        :key="index"
        class="grid gap-2 rounded-xl bg-slate-50 p-3 md:grid-cols-[1fr_160px_auto]"
      >
        <select
          v-model="item.variant_id"
          class="rounded-lg border border-slate-300 bg-white px-3 py-2"
          :disabled="disabled"
          aria-label="Biến thể"
        >
          <option value="">Chọn biến thể</option>
          <option
            v-for="balance in inventory"
            :key="balance.variant_id"
            :value="balance.variant_id"
          >
            {{ balance.product_name }} · {{ balance.sku }} (còn {{ balance.available_stock }})
          </option>
        </select>
        <input
          v-model.number="item.quantity"
          class="rounded-lg border border-slate-300 px-3 py-2"
          :disabled="disabled"
          min="0"
          type="number"
          :aria-label="form.entry_type === 'out' ? 'Số lượng xuất' : 'Tồn thực tế'"
        />
        <button
          class="rounded-lg px-3 py-2 font-bold text-rose-700 disabled:opacity-30"
          type="button"
          :disabled="disabled || form.items.length === 1"
          @click="removeItem(index)"
        >
          Xóa
        </button>
      </div>
    </div>
    <button
      class="rounded-lg bg-indigo-50 px-3 py-1.5 text-sm font-bold text-indigo-700"
      type="button"
      :disabled="disabled"
      @click="addItem"
    >
      Thêm dòng
    </button>
    <div class="flex justify-end gap-3">
      <button class="rounded-xl border px-4 py-2.5 font-bold" type="button" @click="emit('cancel')">
        Đóng
      </button>
      <button
        class="rounded-xl bg-indigo-600 px-5 py-2.5 font-bold text-white disabled:opacity-50"
        :disabled="disabled"
      >
        {{ entry ? 'Lưu phiếu' : 'Tạo phiếu nháp' }}
      </button>
    </div>
  </form>
</template>
