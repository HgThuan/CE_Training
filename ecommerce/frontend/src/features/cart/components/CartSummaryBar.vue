<script setup lang="ts">
import { ShoppingCartIcon } from '@heroicons/vue/24/outline'

import { formatVnd } from '@/shared/lib/formatters'

import type { PreviewResult } from '../types'

defineProps<{
  selectedCount: number
  selectedTotal: number
  preview: PreviewResult | null
  disabled: boolean
}>()
const emit = defineEmits<{ preview: [] }>()
</script>

<template>
  <aside class="sticky bottom-4 rounded-3xl bg-slate-950 p-5 text-white shadow-2xl">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <p class="text-sm text-slate-300">{{ selectedCount }} dòng hợp lệ đã chọn</p>
        <p class="mt-1 text-2xl font-black">
          {{ formatVnd(preview?.total ?? selectedTotal) }}
        </p>
        <p v-if="preview && Number(preview.discount) > 0" class="mt-1 text-sm text-emerald-300">
          Đã giảm {{ formatVnd(preview.discount) }}
        </p>
      </div>
      <div class="flex flex-wrap gap-2">
        <button
          class="rounded-2xl bg-indigo-500 px-6 py-3 font-black hover:bg-indigo-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
          type="button"
          :disabled="disabled"
          @click="emit('preview')"
        >
          Xem trước đơn hàng
        </button>
        <RouterLink
          v-if="preview && selectedCount > 0"
          class="inline-flex items-center gap-2 rounded-2xl bg-emerald-500 px-6 py-3 font-black text-white hover:bg-emerald-400"
          to="/checkout"
        >
          <ShoppingCartIcon class="h-5 w-5" />
          Tiến hành thanh toán
        </RouterLink>
      </div>
    </div>
    <p class="mt-3 text-xs text-slate-400">
      Bước này chỉ xác nhận sản phẩm, tồn kho, voucher và giá tạm tính; chưa thực hiện thanh toán.
    </p>
  </aside>
</template>
