<script setup lang="ts">
import { ref } from 'vue'

import { formatVnd } from '@/shared/lib/formatters'
import type { CheckoutVoucher } from '@/features/promotion/types'

defineProps<{
  vouchers: CheckoutVoucher[]
  selectedIds: string[]
  loading: boolean
  error: string
}>()
const emit = defineEmits<{
  toggle: [id: string, selected: boolean]
  code: [code: string]
}>()
const showCode = ref(false)
const code = ref('')

function submitCode(): void {
  const normalized = code.value.trim().toUpperCase()
  if (normalized) emit('code', normalized)
}
</script>

<template>
  <section class="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
    <div class="flex items-center justify-between gap-3">
      <div>
        <h2 class="text-lg font-black">Voucher của bạn</h2>
        <p class="mt-1 text-xs text-slate-500">Voucher tốt nhất được chọn tự động.</p>
      </div>
      <RouterLink class="text-xs font-bold text-indigo-600" to="/voucher-center"
        >Lưu thêm</RouterLink
      >
    </div>
    <div class="mt-4 space-y-2">
      <label
        v-for="voucher in vouchers"
        :key="voucher.id"
        class="flex gap-3 rounded-xl border p-3"
        :class="
          voucher.is_eligible ? 'cursor-pointer' : 'cursor-not-allowed bg-slate-50 opacity-60'
        "
      >
        <input
          class="mt-1 h-4 w-4"
          type="checkbox"
          :checked="selectedIds.includes(voucher.id)"
          :disabled="!voucher.is_eligible || loading"
          @change="emit('toggle', voucher.id, ($event.target as HTMLInputElement).checked)"
        />
        <span class="min-w-0">
          <strong class="block text-sm">{{ voucher.campaign.name }}</strong>
          <span v-if="voucher.is_eligible" class="text-xs text-emerald-700">
            Tiết kiệm khoảng {{ formatVnd(voucher.estimated_discount) }}
          </span>
          <span v-else class="text-xs text-amber-700">{{ voucher.reason }}</span>
        </span>
      </label>
      <p v-if="!vouchers.length" class="text-sm text-slate-500">Chưa có voucher phù hợp.</p>
    </div>
    <p v-if="error" class="mt-3 rounded-xl bg-rose-50 p-2 text-xs font-bold text-rose-700">
      {{ error }}
    </p>
    <button class="mt-4 text-xs font-bold text-slate-500 underline" @click="showCode = !showCode">
      Bạn có mã khác?
    </button>
    <form v-if="showCode" class="mt-2 flex gap-2" @submit.prevent="submitCode">
      <input
        v-model="code"
        class="min-w-0 flex-1 rounded-xl border px-3 py-2 font-mono text-sm uppercase"
        placeholder="Mã riêng tư"
      />
      <button class="rounded-xl bg-slate-900 px-3 text-sm font-bold text-white" :disabled="loading">
        Dùng mã
      </button>
    </form>
  </section>
</template>
