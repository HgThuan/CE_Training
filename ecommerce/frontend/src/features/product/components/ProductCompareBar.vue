<script setup lang="ts">
import { PhotoIcon, ScaleIcon, TrashIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import { storeToRefs } from 'pinia'
import { nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useCompareStore } from '../compare-store'

const compareStore = useCompareStore()
const { selectedProducts, comparing, error, canCompare } = storeToRefs(compareStore)
const route = useRoute()
const router = useRouter()

async function compareNow(): Promise<void> {
  const succeeded = await compareStore.compare()
  if (!succeeded) return
  if (route.name !== 'product-list') {
    await router.push({ name: 'product-list' })
  }
  await nextTick()
  document.getElementById('product-comparison-result')?.scrollIntoView({
    behavior: 'smooth',
    block: 'start',
  })
}
</script>

<template>
  <aside
    v-if="selectedProducts.length"
    class="fixed inset-x-3 bottom-3 z-50 mx-auto max-w-6xl rounded-3xl border border-slate-700 bg-slate-950/95 p-3 text-white shadow-2xl backdrop-blur sm:inset-x-6 sm:p-4"
    aria-label="Danh sách sản phẩm đang chọn để so sánh"
  >
    <div class="flex flex-col gap-3 lg:flex-row lg:items-center">
      <div class="flex min-w-0 flex-1 gap-2 overflow-x-auto pb-1 lg:pb-0">
        <article
          v-for="product in selectedProducts"
          :key="product.id"
          class="flex min-w-52 max-w-64 flex-1 items-center gap-3 rounded-2xl bg-white/10 p-2"
        >
          <div
            class="grid h-12 w-12 shrink-0 place-items-center overflow-hidden rounded-xl bg-white/10"
          >
            <img
              v-if="product.thumbnail"
              :src="product.thumbnail"
              :alt="product.name"
              class="h-full w-full object-cover"
            />
            <PhotoIcon v-else class="h-6 w-6 text-slate-400" aria-hidden="true" />
          </div>
          <p class="line-clamp-2 min-w-0 flex-1 text-sm font-bold leading-5">
            {{ product.name }}
          </p>
          <button
            class="grid h-9 w-9 shrink-0 place-items-center rounded-xl text-slate-300 transition hover:bg-white/10 hover:text-white"
            type="button"
            :aria-label="`Bỏ ${product.name} khỏi danh sách so sánh`"
            @click="compareStore.remove(product.id)"
          >
            <XMarkIcon class="h-5 w-5" />
          </button>
        </article>
      </div>

      <div class="flex shrink-0 items-center justify-between gap-2 lg:justify-end">
        <button
          class="inline-flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm font-bold text-slate-300 hover:bg-white/10 hover:text-white"
          type="button"
          @click="compareStore.clear"
        >
          <TrashIcon class="h-4 w-4" />
          Xóa tất cả
        </button>
        <button
          class="inline-flex items-center gap-2 rounded-xl bg-indigo-500 px-5 py-3 text-sm font-black text-white transition hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-50"
          type="button"
          :disabled="!canCompare"
          :title="selectedProducts.length < 2 ? 'Chọn ít nhất 2 sản phẩm' : ''"
          @click="compareNow"
        >
          <ScaleIcon class="h-5 w-5" />
          {{ comparing ? 'Đang so sánh…' : 'So sánh ngay' }}
        </button>
      </div>
    </div>
    <p v-if="error" class="mt-2 text-sm font-semibold text-rose-300" role="alert">
      {{ error }}
    </p>
  </aside>
</template>
