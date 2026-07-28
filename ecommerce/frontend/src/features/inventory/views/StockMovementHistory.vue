<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import FormMessage from '@/features/auth/components/FormMessage.vue'
import { getErrorMessage } from '@/features/auth/errors'
import { formatDateTime } from '@/shared/lib/formatters'

import { useInventoryStore } from '../store'

const store = useInventoryStore()
const filters = reactive({ variant_id: '', date_from: '', date_to: '' })
const errorMessage = ref('')

async function load(): Promise<void> {
  errorMessage.value = ''
  try {
    await store.loadMovements({
      variant_id: filters.variant_id || undefined,
      date_from: filters.date_from ? new Date(filters.date_from).toISOString() : undefined,
      date_to: filters.date_to ? new Date(filters.date_to).toISOString() : undefined,
    })
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
}

onMounted(async () => {
  try {
    await Promise.all([store.loadInventory(), load()])
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
})
</script>

<template>
  <main class="mx-auto max-w-7xl px-4 py-8 sm:px-6">
    <p class="text-sm font-bold uppercase tracking-[0.2em] text-indigo-600">SEL-08</p>
    <h1 class="mt-2 text-3xl font-black">Sổ kho</h1>
    <p class="mt-2 text-slate-600">Ledger append-only với số dư đúng bucket sau mỗi giao dịch.</p>
    <FormMessage v-if="errorMessage" class="mt-5" :message="errorMessage" />

    <form
      class="mt-6 grid gap-3 rounded-2xl bg-white p-4 ring-1 ring-slate-200 md:grid-cols-4"
      @submit.prevent="load"
    >
      <select
        v-model="filters.variant_id"
        class="rounded-xl border border-slate-300 bg-white px-3 py-2.5"
      >
        <option value="">Mọi biến thể</option>
        <option
          v-for="balance in store.inventory"
          :key="balance.variant_id"
          :value="balance.variant_id"
        >
          {{ balance.product_name }} · {{ balance.sku }}
        </option>
      </select>
      <input
        v-model="filters.date_from"
        class="rounded-xl border border-slate-300 px-3 py-2.5"
        type="datetime-local"
      />
      <input
        v-model="filters.date_to"
        class="rounded-xl border border-slate-300 px-3 py-2.5"
        type="datetime-local"
      />
      <button class="rounded-xl bg-slate-950 px-4 py-2.5 font-bold text-white">Lọc lịch sử</button>
    </form>

    <div class="mt-5 overflow-hidden rounded-2xl bg-white ring-1 ring-slate-200">
      <div class="overflow-x-auto">
        <table class="w-full min-w-[1000px] text-left text-sm">
          <thead class="bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th class="px-5 py-4">Thời gian</th>
              <th class="px-4 py-4">SKU</th>
              <th class="px-4 py-4">Loại / Bucket</th>
              <th class="px-4 py-4">Thay đổi</th>
              <th class="px-4 py-4">Số dư sau</th>
              <th class="px-4 py-4">Người thao tác</th>
              <th class="px-5 py-4">Tham chiếu</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-for="movement in store.movements" :key="movement.id">
              <td class="px-5 py-4">{{ formatDateTime(movement.created_at) }}</td>
              <td class="px-4 py-4">
                <strong>{{ movement.sku }}</strong>
              </td>
              <td class="px-4 py-4">{{ movement.movement_type }} · {{ movement.bucket }}</td>
              <td
                class="px-4 py-4 font-black"
                :class="movement.quantity > 0 ? 'text-emerald-700' : 'text-rose-700'"
              >
                {{ movement.quantity > 0 ? '+' : '' }}{{ movement.quantity }}
              </td>
              <td class="px-4 py-4 text-lg font-black">{{ movement.balance_after }}</td>
              <td class="px-4 py-4">{{ movement.created_by }}</td>
              <td class="px-5 py-4">
                {{ movement.reference_type }} #{{ movement.reference_id }}
                <span class="block text-xs text-slate-500">{{ movement.note }}</span>
              </td>
            </tr>
            <tr v-if="!store.loading && !store.movements.length">
              <td class="px-5 py-12 text-center text-slate-500" colspan="7">
                Chưa có biến động kho.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </main>
</template>
