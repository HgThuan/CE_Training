<script setup lang="ts">
import { AdjustmentsHorizontalIcon, ArrowPathIcon } from '@heroicons/vue/24/outline'
import { onMounted, ref } from 'vue'

import FormMessage from '@/features/auth/components/FormMessage.vue'
import { getErrorMessage } from '@/features/auth/errors'
import { formatDateTime } from '@/shared/lib/formatters'

import { useInventoryStore } from '../store'
import type { InventoryBalance } from '../types'

const store = useInventoryStore()
const lowStockOnly = ref(false)
const selected = ref<InventoryBalance | null>(null)
const threshold = ref(0)
const saving = ref(false)
const message = ref('')
const errorMessage = ref('')

async function load(): Promise<void> {
  errorMessage.value = ''
  try {
    await store.loadInventory({ low_stock: lowStockOnly.value })
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
}

function openThreshold(balance: InventoryBalance): void {
  selected.value = balance
  threshold.value = balance.low_stock_threshold
}

async function saveThreshold(): Promise<void> {
  if (!selected.value) return
  saving.value = true
  errorMessage.value = ''
  try {
    await store.updateThreshold(selected.value.variant_id, threshold.value)
    message.value = 'Đã cập nhật ngưỡng tồn kho.'
    selected.value = null
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <main class="mx-auto max-w-7xl px-4 py-8 sm:px-6">
    <div class="flex flex-wrap items-end justify-between gap-5">
      <div>
        <p class="text-sm font-bold uppercase tracking-[0.2em] text-indigo-600">SEL-06 · SEL-09</p>
        <h1 class="mt-2 text-3xl font-black text-slate-950">Tồn kho</h1>
        <p class="mt-2 text-slate-600">Số dư khả dụng, đang giữ và ngưỡng cảnh báo theo SKU.</p>
      </div>
      <div class="flex flex-wrap gap-2">
        <RouterLink
          class="rounded-xl border bg-white px-4 py-2.5 font-bold"
          to="/seller/inventory/entries"
        >
          Phiếu nhập
        </RouterLink>
        <RouterLink
          class="rounded-xl border bg-white px-4 py-2.5 font-bold"
          to="/seller/inventory/out"
        >
          Xuất / kiểm kê
        </RouterLink>
        <RouterLink
          class="rounded-xl bg-slate-950 px-4 py-2.5 font-bold text-white"
          to="/seller/inventory/movements"
        >
          Sổ kho
        </RouterLink>
      </div>
    </div>

    <FormMessage v-if="message" class="mt-5" :message="message" variant="success" />
    <FormMessage v-if="errorMessage" class="mt-5" :message="errorMessage" />

    <div
      class="mt-6 flex items-center justify-between rounded-2xl bg-white p-4 ring-1 ring-slate-200"
    >
      <label class="inline-flex items-center gap-2 font-bold text-slate-700">
        <input v-model="lowStockOnly" type="checkbox" @change="load" />
        Chỉ SKU sắp hết
      </label>
      <button class="inline-flex items-center gap-2 font-bold text-indigo-700" @click="load">
        <ArrowPathIcon class="h-5 w-5" />
        Làm mới
      </button>
    </div>

    <div class="mt-5 overflow-hidden rounded-2xl bg-white ring-1 ring-slate-200">
      <div class="overflow-x-auto">
        <table class="w-full min-w-[900px] text-left text-sm">
          <thead class="bg-slate-50 text-xs uppercase tracking-wider text-slate-500">
            <tr>
              <th class="px-5 py-4">Sản phẩm / SKU</th>
              <th class="px-4 py-4">Khả dụng</th>
              <th class="px-4 py-4">Đang giữ</th>
              <th class="px-4 py-4">Ngưỡng</th>
              <th class="px-4 py-4">Cập nhật</th>
              <th class="px-5 py-4 text-right">Thao tác</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-if="store.loading">
              <td class="px-5 py-10 text-center text-slate-500" colspan="6">Đang tải tồn kho…</td>
            </tr>
            <tr v-else-if="!store.inventory.length">
              <td class="px-5 py-12 text-center text-slate-500" colspan="6">
                Không có dữ liệu tồn kho phù hợp.
              </td>
            </tr>
            <tr
              v-for="balance in store.inventory"
              :key="balance.variant_id"
              :class="balance.is_low_stock ? 'bg-amber-50' : 'hover:bg-slate-50'"
            >
              <td class="px-5 py-4">
                <strong class="block text-slate-950">{{ balance.product_name }}</strong>
                <span class="text-xs text-slate-500"
                  >{{ balance.sku }} · {{ balance.variant_name }}</span
                >
              </td>
              <td
                class="px-4 py-4 text-lg font-black"
                :class="balance.is_low_stock ? 'text-rose-700' : 'text-emerald-700'"
              >
                {{ balance.available_stock }}
              </td>
              <td class="px-4 py-4 font-bold">{{ balance.reserved_stock }}</td>
              <td class="px-4 py-4">{{ balance.low_stock_threshold }}</td>
              <td class="px-4 py-4 text-slate-600">{{ formatDateTime(balance.updated_at) }}</td>
              <td class="px-5 py-4 text-right">
                <button
                  class="inline-flex items-center gap-2 rounded-lg border px-3 py-2 font-bold text-indigo-700"
                  @click="openThreshold(balance)"
                >
                  <AdjustmentsHorizontalIcon class="h-4 w-4" />
                  Đặt ngưỡng
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="selected" class="fixed inset-0 z-50 grid place-items-center bg-slate-950/40 p-4">
      <form
        class="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl"
        @submit.prevent="saveThreshold"
      >
        <h2 class="text-xl font-black">Ngưỡng tồn thấp</h2>
        <p class="mt-1 text-sm text-slate-600">{{ selected.product_name }} · {{ selected.sku }}</p>
        <input
          v-model.number="threshold"
          class="mt-5 w-full rounded-xl border border-slate-300 px-3 py-2.5"
          min="0"
          type="number"
          required
        />
        <div class="mt-5 flex justify-end gap-3">
          <button
            class="rounded-xl border px-4 py-2.5 font-bold"
            type="button"
            @click="selected = null"
          >
            Hủy
          </button>
          <button
            class="rounded-xl bg-indigo-600 px-4 py-2.5 font-bold text-white"
            :disabled="saving"
          >
            Lưu
          </button>
        </div>
      </form>
    </div>
  </main>
</template>
