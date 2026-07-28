<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'

import type { InventoryBalance, StockEntry, StockEntryPayload } from '../types'

const props = defineProps<{
  inventory: InventoryBalance[]
  entry?: StockEntry | null
  submitting?: boolean
}>()
const emit = defineEmits<{
  submit: [payload: StockEntryPayload]
  cancel: []
}>()

const errorMessage = ref('')
const form = reactive<{
  supplier_name: string
  note: string
  items: Array<{ variant_id: string; quantity: number; unit_cost: string }>
}>({
  supplier_name: '',
  note: '',
  items: [{ variant_id: '', quantity: 1, unit_cost: '0' }],
})

const disabled = computed(() => props.entry?.status === 'confirmed' || props.submitting)

watch(
  () => props.entry,
  (entry) => {
    form.supplier_name = entry?.supplier_name ?? ''
    form.note = entry?.note ?? ''
    form.items = entry?.items.length
      ? entry.items.map((item) => ({
          variant_id: item.variant_id,
          quantity: item.quantity,
          unit_cost: item.unit_cost,
        }))
      : [{ variant_id: '', quantity: 1, unit_cost: '0' }]
    errorMessage.value = ''
  },
  { immediate: true },
)

function addItem(): void {
  form.items.push({ variant_id: '', quantity: 1, unit_cost: '0' })
}

function removeItem(index: number): void {
  if (form.items.length > 1) form.items.splice(index, 1)
}

function submit(): void {
  errorMessage.value = ''
  if (!form.supplier_name.trim()) {
    errorMessage.value = 'Vui lòng nhập tên nhà cung cấp.'
    return
  }
  if (
    form.items.some(
      (item) =>
        !item.variant_id ||
        !Number.isInteger(Number(item.quantity)) ||
        Number(item.quantity) <= 0 ||
        Number(item.unit_cost) < 0,
    )
  ) {
    errorMessage.value = 'Mỗi dòng cần biến thể, số lượng dương và giá nhập không âm.'
    return
  }
  if (new Set(form.items.map((item) => item.variant_id)).size !== form.items.length) {
    errorMessage.value = 'Một biến thể chỉ được xuất hiện một lần.'
    return
  }
  emit('submit', {
    supplier_name: form.supplier_name.trim(),
    note: form.note.trim(),
    items: form.items.map((item) => ({
      variant_id: item.variant_id,
      quantity: Number(item.quantity),
      unit_cost: String(item.unit_cost),
    })),
  })
}
</script>

<template>
  <form class="space-y-5" @submit.prevent="submit">
    <p v-if="entry?.status === 'confirmed'" class="rounded-xl bg-emerald-50 p-3 text-emerald-800">
      Phiếu đã xác nhận và chỉ còn quyền xem.
    </p>
    <p v-if="errorMessage" class="rounded-xl bg-rose-50 p-3 text-rose-700" role="alert">
      {{ errorMessage }}
    </p>
    <label class="block">
      <span class="mb-1.5 block text-sm font-bold text-slate-700">Nhà cung cấp</span>
      <input
        v-model.trim="form.supplier_name"
        class="w-full rounded-xl border border-slate-300 px-3 py-2.5"
        :disabled="disabled"
        required
      />
    </label>
    <label class="block">
      <span class="mb-1.5 block text-sm font-bold text-slate-700">Ghi chú</span>
      <textarea
        v-model.trim="form.note"
        class="w-full rounded-xl border border-slate-300 px-3 py-2.5"
        :disabled="disabled"
        rows="2"
      />
    </label>
    <div>
      <div class="mb-2 flex items-center justify-between">
        <h3 class="font-black text-slate-900">Dòng nhập kho</h3>
        <button
          class="rounded-lg bg-indigo-50 px-3 py-1.5 text-sm font-bold text-indigo-700"
          type="button"
          :disabled="disabled"
          @click="addItem"
        >
          Thêm dòng
        </button>
      </div>
      <div class="space-y-3">
        <div
          v-for="(item, index) in form.items"
          :key="index"
          class="grid gap-2 rounded-xl bg-slate-50 p-3 md:grid-cols-[1fr_120px_160px_auto]"
        >
          <select
            v-model="item.variant_id"
            class="rounded-lg border border-slate-300 bg-white px-3 py-2"
            :disabled="disabled"
            aria-label="Biến thể"
          >
            <option value="">Chọn biến thể</option>
            <option v-for="balance in inventory" :key="balance.variant_id" :value="balance.variant_id">
              {{ balance.product_name }} · {{ balance.sku }}
            </option>
          </select>
          <input
            v-model.number="item.quantity"
            class="rounded-lg border border-slate-300 px-3 py-2"
            :disabled="disabled"
            min="1"
            type="number"
            aria-label="Số lượng nhập"
          />
          <input
            v-model="item.unit_cost"
            class="rounded-lg border border-slate-300 px-3 py-2"
            :disabled="disabled"
            min="0"
            type="number"
            aria-label="Giá nhập"
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
    </div>
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
