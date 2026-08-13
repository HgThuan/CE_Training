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

function statusColor(voucher: Voucher): string {
  if (!voucher.is_active) return 'bg-slate-100 text-slate-600'
  if (new Date(voucher.valid_until).getTime() < Date.now()) return 'bg-red-100 text-red-700'
  if (new Date(voucher.valid_from).getTime() > Date.now()) return 'bg-blue-100 text-blue-700'
  return 'bg-emerald-100 text-emerald-700'
}

function usageDisplay(voucher: Voucher): string {
  const used = voucher.total_usage_limit != null && voucher.remaining_quantity != null
    ? voucher.total_usage_limit - voucher.remaining_quantity
    : (voucher.issued_quantity ?? 0)
  const total = voucher.total_usage_limit
  return total != null ? `${used} / ${total}` : `${used} / ∞`
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
          <th class="px-5 py-4">Lượt dùng</th>
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
            <template v-if="Number(voucher.min_order_amount) > 0">
              Từ {{ formatVnd(voucher.min_order_amount) }}
            </template>
            <span v-else class="text-slate-400">Không giới hạn</span>
          </td>
          <td class="px-5 py-4 font-mono text-sm">
            {{ usageDisplay(voucher) }}
          </td>
          <td class="px-5 py-4">{{ new Date(voucher.valid_until).toLocaleString('vi-VN') }}</td>
          <td class="px-5 py-4">
            <span class="rounded-full px-2 py-1 text-xs font-bold" :class="statusColor(voucher)">{{ status(voucher) }}</span>
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
