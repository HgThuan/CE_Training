<script setup lang="ts">
import { ref } from 'vue'

import { formatVnd } from '@/shared/lib/formatters'

import FlashSaleForm from '../../components/FlashSaleForm.vue'
import { usePromotionStore } from '../../store'
import type { FlashSale, FlashSalePayload } from '../../types'
import ConfirmDialog from '@/shared/components/ConfirmDialog.vue'

const store = usePromotionStore()
const formOpen = ref(false)
const editing = ref<FlashSale | null>(null)
const confirmOpen = ref(false)
const confirmTarget = ref<FlashSale | null>(null)

function open(sale: FlashSale | null = null): void {
  editing.value = sale
  formOpen.value = true
}
async function save(payload: FlashSalePayload): Promise<void> {
  await store.saveFlashSale(payload, editing.value?.id)
  formOpen.value = false
}
function requestRemove(sale: FlashSale): void {
  confirmTarget.value = sale
  confirmOpen.value = true
}
async function handleConfirmRemove(): Promise<void> {
  if (!confirmTarget.value) return
  await store.deleteFlashSale(confirmTarget.value.id)
  confirmOpen.value = false
  confirmTarget.value = null
}
function handleCancelRemove(): void {
  confirmOpen.value = false
  confirmTarget.value = null
}
void store.loadAdminFlashSales()
</script>

<template>
  <main class="mx-auto max-w-7xl px-4 py-8 sm:px-6">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="text-3xl font-black">Quản lý Flash Sale</h1>
        <p class="mt-2 text-slate-500">Khung giờ, giá sale và quota được kiểm soát tại máy chủ.</p>
      </div>
      <button class="rounded-xl bg-indigo-600 px-5 py-3 font-bold text-white" @click="open()">
        Tạo Flash Sale
      </button>
    </div>
    <div v-if="store.loading" class="mt-7 h-52 animate-pulse rounded-3xl bg-slate-200" />
    <section v-else-if="store.error" class="mt-7 rounded-3xl bg-rose-50 p-8 text-center">
      <p class="font-bold text-rose-800">{{ store.error }}</p>
      <button
        class="mt-4 rounded-xl bg-rose-700 px-4 py-2 font-bold text-white"
        @click="store.loadAdminFlashSales"
      >
        Thử lại
      </button>
    </section>
    <section
      v-else-if="!store.flashSales.length"
      class="mt-7 rounded-3xl border border-dashed bg-white p-12 text-center text-slate-500"
    >
      Chưa có chương trình Flash Sale.
    </section>
    <div v-else class="mt-7 grid gap-5 lg:grid-cols-2">
      <article
        v-for="sale in store.flashSales"
        :key="sale.id"
        class="rounded-3xl border bg-white p-5 shadow-sm"
      >
        <div class="flex items-start justify-between gap-3">
          <div>
            <span class="rounded-full bg-slate-100 px-2 py-1 text-xs font-bold">{{
              sale.status
            }}</span>
            <h2 class="mt-3 text-xl font-black">{{ sale.name }}</h2>
            <p class="mt-1 text-sm text-slate-500">
              {{ new Date(sale.start_time).toLocaleString('vi-VN') }} –
              {{ new Date(sale.end_time).toLocaleString('vi-VN') }}
            </p>
          </div>
          <div>
            <button class="mr-3 font-bold text-indigo-700" @click="open(sale)">Sửa</button
            ><button class="font-bold text-rose-700" @click="requestRemove(sale)">Xóa</button>
          </div>
        </div>
        <ul class="mt-4 divide-y rounded-2xl bg-slate-50 px-4">
          <li
            v-for="item in sale.items"
            :key="item.id"
            class="flex justify-between gap-3 py-3 text-sm"
          >
            <span>{{ item.product_name || item.variant_sku || item.variant }}</span
            ><strong
              >{{ formatVnd(item.sale_price) }} · {{ item.sold_count }}/{{ item.quota }}</strong
            >
          </li>
        </ul>
      </article>
    </div>
    <div
      v-if="formOpen"
      class="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-slate-950/60 p-4"
    >
      <div class="my-8 w-full max-w-4xl rounded-3xl bg-white p-6">
        <h2 class="mb-5 text-xl font-black">
          {{ editing ? 'Cập nhật Flash Sale' : 'Tạo Flash Sale' }}
        </h2>
        <FlashSaleForm
          :key="editing?.id ?? 'new'"
          :flash-sale="editing"
          :saving="store.saving"
          @submit="save"
          @cancel="formOpen = false"
        />
      </div>
    </div>
    
    <ConfirmDialog
      :open="confirmOpen"
      title="Xóa Flash Sale"
      :message="'Bạn có chắc chắn muốn xóa chương trình ' + confirmTarget?.name + '?'"
      @confirm="handleConfirmRemove"
      @cancel="handleCancelRemove"
    />
  </main>
</template>
