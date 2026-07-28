<script setup lang="ts">
import { onMounted, ref } from 'vue'

import FormMessage from '@/features/auth/components/FormMessage.vue'
import { getErrorMessage } from '@/features/auth/errors'
import { formatDateTime, formatVnd } from '@/shared/lib/formatters'

import StockEntryForm from '../components/StockEntryForm.vue'
import { useInventoryStore } from '../store'
import type { StockEntry, StockEntryPayload } from '../types'

const store = useInventoryStore()
const editing = ref<StockEntry | null | undefined>(undefined)
const submitting = ref(false)
const actionId = ref<number | null>(null)
const message = ref('')
const errorMessage = ref('')

async function load(): Promise<void> {
  try {
    await Promise.all([store.loadStockEntries(), store.loadInventory()])
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
}

async function save(payload: StockEntryPayload): Promise<void> {
  submitting.value = true
  try {
    await store.saveStockEntry(payload, editing.value?.id)
    message.value = editing.value ? 'Đã cập nhật phiếu nhập.' : 'Đã tạo phiếu nhập nháp.'
    editing.value = undefined
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    submitting.value = false
  }
}

async function confirm(entry: StockEntry): Promise<void> {
  actionId.value = entry.id
  try {
    await store.confirmStockEntry(entry.id)
    message.value = 'Đã xác nhận phiếu và cộng tồn.'
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    actionId.value = null
  }
}

onMounted(load)
</script>

<template>
  <main class="mx-auto max-w-7xl px-4 py-8 sm:px-6">
    <div class="flex items-end justify-between gap-4">
      <div>
        <p class="text-sm font-bold uppercase tracking-[0.2em] text-indigo-600">SEL-06</p>
        <h1 class="mt-2 text-3xl font-black">Phiếu nhập kho</h1>
      </div>
      <button class="rounded-xl bg-indigo-600 px-5 py-3 font-bold text-white" @click="editing = null">
        Tạo phiếu nhập
      </button>
    </div>
    <FormMessage v-if="message" class="mt-5" :message="message" variant="success" />
    <FormMessage v-if="errorMessage" class="mt-5" :message="errorMessage" />

    <section v-if="editing !== undefined" class="mt-6 rounded-2xl bg-white p-6 ring-1 ring-slate-200">
      <StockEntryForm
        :entry="editing"
        :inventory="store.inventory"
        :submitting="submitting"
        @cancel="editing = undefined"
        @submit="save"
      />
    </section>

    <div class="mt-6 overflow-hidden rounded-2xl bg-white ring-1 ring-slate-200">
      <table class="w-full text-left text-sm">
        <thead class="bg-slate-50 text-xs uppercase text-slate-500">
          <tr>
            <th class="px-5 py-4">Phiếu / Nhà cung cấp</th>
            <th class="px-4 py-4">Dòng hàng</th>
            <th class="px-4 py-4">Trạng thái</th>
            <th class="px-4 py-4">Ngày tạo</th>
            <th class="px-5 py-4 text-right">Thao tác</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr v-for="entry in store.stockEntries" :key="entry.id">
            <td class="px-5 py-4">
              <strong>#{{ entry.id }} · {{ entry.supplier_name }}</strong>
              <span class="block text-xs text-slate-500">{{ entry.note }}</span>
            </td>
            <td class="px-4 py-4">
              <span v-for="item in entry.items" :key="item.id" class="block">
                {{ item.sku }}: +{{ item.quantity }} @ {{ formatVnd(item.unit_cost) }}
              </span>
            </td>
            <td class="px-4 py-4 font-bold">
              {{ entry.status === 'draft' ? 'Bản nháp' : 'Đã xác nhận' }}
            </td>
            <td class="px-4 py-4">{{ formatDateTime(entry.created_at) }}</td>
            <td class="px-5 py-4">
              <div class="flex justify-end gap-2">
                <button class="rounded-lg border px-3 py-2 font-bold" @click="editing = entry">
                  {{ entry.status === 'draft' ? 'Sửa' : 'Xem' }}
                </button>
                <button
                  class="rounded-lg bg-emerald-600 px-3 py-2 font-bold text-white disabled:opacity-40"
                  :disabled="entry.status === 'confirmed' || actionId === entry.id"
                  @click="confirm(entry)"
                >
                  Xác nhận phiếu
                </button>
              </div>
            </td>
          </tr>
          <tr v-if="!store.loading && !store.stockEntries.length">
            <td class="px-5 py-12 text-center text-slate-500" colspan="5">Chưa có phiếu nhập.</td>
          </tr>
        </tbody>
      </table>
    </div>
  </main>
</template>

