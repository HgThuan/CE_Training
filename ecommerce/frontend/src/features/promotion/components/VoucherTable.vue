<script setup lang="ts">
import { formatVnd } from '@/shared/lib/formatters'

import type { Voucher } from '../types'

defineProps<{ vouchers: Voucher[] }>()
const emit = defineEmits<{ edit: [voucher: Voucher]; remove: [voucher: Voucher] }>()

function status(voucher: Voucher): string {
  if (!voucher.is_active) return 'Đã tắt'
  if (new Date(voucher.valid_until).getTime() < Date.now()) return 'Đã hết hạn'
  if (new Date(voucher.valid_from).getTime() > Date.now()) return 'Sắp diễn ra'
  return 'Đang hoạt động'
}

function usage(voucher: Voucher): string {
  const used =
    voucher.issued_quantity ??
    (voucher.total_usage_limit !== null && voucher.remaining_quantity !== null
      ? voucher.total_usage_limit - voucher.remaining_quantity
      : 0)
  return voucher.total_usage_limit === null
    ? `${used} lượt đã dùng · Không giới hạn`
    : `${used}/${voucher.total_usage_limit} lượt đã dùng`
}

function statusClass(voucher: Voucher): string {
  const value = status(voucher)
  if (value === 'Đang hoạt động') return 'bg-emerald-50 text-emerald-700'
  if (value === 'Sắp diễn ra') return 'bg-amber-50 text-amber-700'
  if (value === 'Đã hết hạn') return 'bg-rose-50 text-rose-700'
  return 'bg-slate-100 text-slate-600'
}
</script>

<template>
  <div class="overflow-x-auto rounded-3xl border border-slate-200 bg-white shadow-sm">
    <table class="min-w-full text-left text-sm">
      <thead class="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
        <tr>
          <th class="px-5 py-4">Mã</th>
          <th class="px-5 py-4">Ưu đãi</th>
          <th class="px-5 py-4">Điều kiện</th>
          <th class="px-5 py-4">Thời hạn</th>
          <th class="px-5 py-4">Trạng thái</th>
          <th class="px-5 py-4" />
        </tr>
      </thead>
      <tbody class="divide-y divide-slate-100">
        <tr v-for="voucher in vouchers" :key="voucher.id">
          <td class="px-5 py-4">
            <strong class="font-mono text-indigo-700">{{ voucher.code }}</strong>
            <p class="mt-1 text-xs text-slate-500">{{ voucher.name }}</p>
          </td>
          <td class="px-5 py-4 font-bold">
            {{
              ['percent', 'percentage'].includes(voucher.discount_type)
                ? `${voucher.discount_value}%`
                : formatVnd(voucher.discount_value)
            }}
          </td>
          <td class="px-5 py-4">
            {{
              Number(voucher.min_order_amount) > 0
                ? `Từ ${formatVnd(voucher.min_order_amount)}`
                : 'Không yêu cầu đơn tối thiểu'
            }}
            <p class="text-xs text-slate-500">
              {{ usage(voucher) }}
            </p>
          </td>
          <td class="px-5 py-4">{{ new Date(voucher.valid_until).toLocaleString('vi-VN') }}</td>
          <td class="px-5 py-4">
            <span class="rounded-full px-2 py-1 text-xs font-bold" :class="statusClass(voucher)">{{
              status(voucher)
            }}</span>
          </td>
          <td class="px-5 py-4 text-right">
            <button class="mr-3 font-bold text-indigo-700" @click="emit('edit', voucher)">
              Sửa</button
            ><button class="font-bold text-rose-700" @click="emit('remove', voucher)">Xóa</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
