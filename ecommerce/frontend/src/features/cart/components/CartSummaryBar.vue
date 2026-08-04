<script setup lang="ts">
import { formatVnd } from '@/shared/lib/formatters'

defineProps<{
  selectedCount: number
  selectedTotal: number
  disabled: boolean
}>()
const emit = defineEmits<{ checkout: [] }>()
</script>

<template>
  <aside class="sticky bottom-4 rounded-3xl bg-slate-950 p-5 text-white shadow-2xl">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <p class="text-sm text-slate-300">{{ selectedCount }} dòng hợp lệ đã chọn</p>
        <p class="mt-1 text-2xl font-black">
          {{ formatVnd(selectedTotal) }}
        </p>
      </div>
      <div class="grid gap-2 sm:min-w-56">
        <button
          class="rounded-2xl bg-indigo-500 px-6 py-3 font-black hover:bg-indigo-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
          type="button"
          :disabled="disabled"
          @click="emit('checkout')"
        >
          Tiến hành thanh toán
        </button>
      </div>
    </div>
    <p class="mt-3 text-xs text-slate-400">
      Tạm tính tự động cập nhật theo sản phẩm đang chọn. Voucher và phí vận chuyển áp dụng ở checkout.
    </p>
  </aside>
</template>
