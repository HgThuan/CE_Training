<script setup lang="ts">
import { ref } from 'vue'

import type { Voucher, VoucherPayload, VoucherScope } from '../types'
import { usePromotionStore } from '../store'
import VoucherForm from './VoucherForm.vue'
import VoucherTable from './VoucherTable.vue'

const props = defineProps<{ scope: VoucherScope; title: string; description: string }>()
const store = usePromotionStore()
const editing = ref<Voucher | null>(null)
const formOpen = ref(false)
const formRef = ref<InstanceType<typeof VoucherForm> | null>(null)

function openForm(voucher: Voucher | null = null): void {
  editing.value = voucher
  formOpen.value = true
}

async function save(payload: VoucherPayload): Promise<void> {
  try {
    await store.saveVoucher(props.scope, payload, editing.value?.id)
    formOpen.value = false
  } catch (error) {
    formRef.value?.showServerError(error)
  }
}

async function remove(voucher: Voucher): Promise<void> {
  if (!window.confirm(`Xóa voucher ${voucher.code}?`)) return
  await store.deleteVoucher(props.scope, voucher.id)
}

void store.loadVouchers(props.scope)
</script>

<template>
  <main class="mx-auto max-w-7xl px-4 py-8 sm:px-6">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 class="text-3xl font-black text-slate-950">{{ title }}</h1>
        <p class="mt-2 text-slate-500">{{ description }}</p>
      </div>
      <button class="rounded-xl bg-indigo-600 px-5 py-3 font-bold text-white" @click="openForm()">
        Tạo voucher
      </button>
    </div>
    <div v-if="store.loading" class="mt-7 h-52 animate-pulse rounded-3xl bg-slate-200" />
    <section
      v-else-if="store.error"
      class="mt-7 rounded-3xl bg-rose-50 p-8 text-center text-rose-800"
    >
      <p class="font-bold">{{ store.error }}</p>
      <button
        class="mt-4 rounded-xl bg-rose-700 px-4 py-2 font-bold text-white"
        @click="store.loadVouchers(scope)"
      >
        Thử lại
      </button>
    </section>
    <section
      v-else-if="!store.vouchers.length"
      class="mt-7 rounded-3xl border border-dashed bg-white p-12 text-center text-slate-500"
    >
      Chưa có voucher nào. Tạo voucher đầu tiên để bắt đầu.
    </section>
    <VoucherTable
      v-else
      class="mt-7"
      :vouchers="store.vouchers"
      @edit="openForm"
      @remove="remove"
    />
    <div
      v-if="formOpen"
      class="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-slate-950/60 p-4"
    >
      <div class="my-8 w-full max-w-3xl rounded-3xl bg-white p-6 shadow-2xl">
        <h2 class="mb-5 text-xl font-black">
          {{ editing ? 'Cập nhật voucher' : 'Tạo voucher mới' }}
        </h2>
        <VoucherForm
          ref="formRef"
          :key="editing?.id ?? 'new'"
          :scope="scope"
          :voucher="editing"
          :saving="store.saving"
          @submit="save"
          @cancel="formOpen = false"
        />
      </div>
    </div>
  </main>
</template>
