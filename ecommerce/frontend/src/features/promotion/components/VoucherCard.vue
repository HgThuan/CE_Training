<script setup lang="ts">
import { computed } from 'vue'

import { formatVnd } from '@/shared/lib/formatters'

import type { Voucher } from '../types'

const props = defineProps<{
  voucher: Voucher
  collected?: boolean
  loading?: boolean
  compact?: boolean
}>()
defineEmits<{ collect: [voucher: Voucher] }>()

const label = computed(() => {
  if (props.voucher.discount_type === 'freeship') return 'Miễn phí vận chuyển'
  if (['percent', 'percentage'].includes(props.voucher.discount_type)) {
    return `Giảm ${Number(props.voucher.value)}%`
  }
  return `Giảm ${formatVnd(props.voucher.value)}`
})
const usedPercent = computed(() => {
  const total = props.voucher.total_quantity
  const remaining = props.voucher.remaining_quantity
  if (!total || remaining === null) return 0
  return Math.min(100, Math.round(((total - remaining) / total) * 100))
})
</script>

<template>
  <article class="rounded-2xl border border-indigo-100 bg-white p-4 shadow-sm">
    <div class="flex items-start justify-between gap-3">
      <div>
        <span class="text-xs font-black uppercase tracking-wider text-indigo-600">
          {{ voucher.issuer_type === 'platform' ? 'Voucher sàn' : voucher.shop_name }}
        </span>
        <h3 class="mt-1 font-black text-slate-950">{{ label }}</h3>
        <p class="mt-1 text-xs text-slate-500">
          Đơn tối thiểu {{ formatVnd(voucher.min_order_value) }} · HSD
          {{ new Date(voucher.end_time).toLocaleDateString('vi-VN') }}
        </p>
      </div>
      <button
        class="shrink-0 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-bold text-white disabled:bg-slate-200 disabled:text-slate-500"
        type="button"
        :disabled="collected || loading"
        @click="$emit('collect', voucher)"
      >
        {{ collected ? 'Đã lưu' : loading ? 'Đang lưu…' : 'Lưu' }}
      </button>
    </div>
    <template v-if="!compact && voucher.total_quantity">
      <div class="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-100">
        <div class="h-full rounded-full bg-rose-500" :style="{ width: `${usedPercent}%` }" />
      </div>
      <p class="mt-1 text-xs font-semibold text-rose-600">
        Đã lưu {{ usedPercent }}% · Còn {{ voucher.remaining_quantity }} voucher
      </p>
    </template>
  </article>
</template>
