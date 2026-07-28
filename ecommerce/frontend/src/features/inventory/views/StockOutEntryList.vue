<script setup lang="ts">
import { onMounted, ref } from 'vue'

import FormMessage from '@/features/auth/components/FormMessage.vue'
import { getErrorMessage } from '@/features/auth/errors'
import { formatDateTime } from '@/shared/lib/formatters'

import StockOutEntryForm from '../components/StockOutEntryForm.vue'
import { useInventoryStore } from '../store'
import type { StockOutEntry, StockOutEntryPayload } from '../types'

const store = useInventoryStore()
const editing = ref<StockOutEntry | null | undefined>(undefined)
const submitting = ref(false)
const actionId = ref<number | null>(null)
const message = ref('')
const errorMessage = ref('')

async function load(): Promise<void> {
  try {
    await Promise.all([store.loadStockOutEntries(), store.loadInventory()])
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
}

async function save(payload: StockOutEntryPayload): Promise<void> {
  submitting.value = true
  try {
    await store.saveStockOutEntry(payload, editing.value?.id)
    message.value = 'Đã lưu phiếu xuất/kiểm kê.'
    editing.value = undefined
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    submitting.value = false
  }
}

async function confirm(entry: StockOutEntry): Promise<void> {
  actionId.value = entry.id
  try {
    await store.confirmStockOutEntry(entry.id)
    message.value = 'Đã xác nhận phiếu và cập nhật tồn kho.'
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
        <p class="text-sm font-bold uppercase tracking-[0.2em] text-indigo-600">SEL-07</p>
        <h1 class="mt-2 text-3xl font-black">Xuất kho & kiểm kê</h1>
      </div>
      <button class="rounded-xl bg-indigo-600 px-5 py-3 font-bold text-white" @click="editing = null">
        Tạo phiếu
      </button>
    </div>
    <FormMessage v-if="message" class="mt-5" :message="message" variant="success" />
    <FormMessage v-if="errorMessage" class="mt-5" :message="errorMessage" />

    <section v-if="editing !== undefined" class="mt-6 rounded-2xl bg-white p-6 ring-1 ring-slate-200">
      <StockOutEntryForm
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
            <th class="px-5 py-4">Phiếu</th>
            <th class="px-4 py-4">Lý do / Dòng hàng</th>
            <th class="px-4 py-4">Trạng thái</th>
            <th class="px-4 py-4">Ngày tạo</th>
            <th class="px-5 py-4 text-right">Thao tác</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          <tr v-for="entry in store.stockOutEntries" :key="entry.id">
            <td class="px-5 py-4 font-black">
              #{{ entry.id }} · {{ entry.entry_type === 'out' ? 'Xuất kho' : 'Kiểm kê' }}
            </td>
            <td class="px-4 py-4">
              <strong>{{ entry.reason }}</strong>
              <span v-for="item in entry.items" :key="item.id" class="block text-xs text-slate-500">
                {{ item.sku }}: {{ item.quantity }}
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
                  Xác nhận
                </button>
              </div>
            </td>
          </tr>
          <tr v-if="!store.loading && !store.stockOutEntries.length">
            <td class="px-5 py-12 text-center text-slate-500" colspan="5">Chưa có phiếu.</td>
          </tr>
        </tbody>
      </table>
    </div>
  </main>
</template>

