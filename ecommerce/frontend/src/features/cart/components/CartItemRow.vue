<script setup lang="ts">
import { TrashIcon } from '@heroicons/vue/24/outline'
import { onBeforeUnmount, ref, watch } from 'vue'

import { formatVnd } from '@/shared/lib/formatters'

import type { CartItem } from '../types'

const props = defineProps<{ item: CartItem }>()
const emit = defineEmits<{
  update: [item: CartItem, payload: { quantity?: number; is_selected?: boolean }]
  remove: [item: CartItem]
}>()

const quantity = ref(props.item.quantity)
let debounceTimer: ReturnType<typeof setTimeout> | undefined

watch(
  () => props.item.quantity,
  (value) => (quantity.value = value),
)

function changeQuantity(): void {
  quantity.value = Math.max(1, Math.trunc(quantity.value || 1))
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    emit('update', props.item, { quantity: quantity.value })
  }, 350)
}

onBeforeUnmount(() => {
  if (debounceTimer) clearTimeout(debounceTimer)
})
</script>

<template>
  <article
    class="grid gap-4 border-t border-slate-100 px-4 py-5 sm:grid-cols-[auto_88px_1fr_auto] sm:items-center sm:px-5"
    :class="!item.is_valid && 'bg-rose-50/60'"
  >
    <input
      class="h-5 w-5 rounded border-slate-300 text-indigo-600"
      type="checkbox"
      :checked="item.is_selected"
      :disabled="!item.is_valid"
      :aria-label="`Chọn ${item.product_name}`"
      @change="
        emit('update', item, {
          is_selected: ($event.target as HTMLInputElement).checked,
        })
      "
    />
    <img
      :src="item.primary_image || 'https://placehold.co/176x176?text=No+image'"
      :alt="item.product_name"
      class="h-22 w-22 rounded-2xl border border-slate-200 object-cover"
    />
    <div class="min-w-0">
      <RouterLink
        v-if="item.product_slug"
        class="font-bold text-slate-950 hover:text-indigo-700"
        :to="`/products/${item.product_slug}`"
      >
        {{ item.product_name }}
      </RouterLink>
      <p v-else class="font-bold text-slate-950">{{ item.product_name }}</p>
      <p class="mt-1 text-xs text-slate-500">
        {{ item.variant_name || item.variant_sku }}
      </p>
      <div class="mt-2 flex flex-wrap items-center gap-2">
        <strong class="text-indigo-700">{{ formatVnd(item.current_price) }}</strong>
        <span v-if="item.is_flash_sale" class="text-xs text-slate-400 line-through">
          {{ formatVnd(item.regular_price) }}
        </span>
        <span
          v-if="item.is_flash_sale"
          class="rounded-full bg-rose-100 px-2 py-0.5 text-xs font-black text-rose-700"
        >
          FLASH SALE · còn {{ item.remaining_flash_quota }}
        </span>
        <template v-if="item.price_changed">
          <span class="text-xs text-slate-400 line-through">
            {{ formatVnd(item.unit_price_snapshot) }}
          </span>
          <span class="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-bold text-amber-800">
            Giá đã cập nhật
          </span>
        </template>
      </div>
      <p v-if="!item.is_valid" class="mt-2 text-sm font-bold text-rose-700">
        {{
          item.available_stock === 0
            ? 'Sản phẩm đã hết hàng'
            : `Chỉ còn ${item.available_stock} sản phẩm — hãy giảm số lượng`
        }}
      </p>
    </div>
    <div class="flex items-center justify-between gap-3 sm:block sm:text-right">
      <label class="text-xs font-semibold text-slate-500">
        Số lượng
        <input
          v-model.number="quantity"
          class="ml-2 w-20 rounded-xl border border-slate-300 px-3 py-2 text-center text-sm font-bold focus:border-indigo-500 focus:outline-none sm:ml-0 sm:mt-1 sm:block"
          type="number"
          min="1"
          :max="Math.max(1, item.available_stock)"
          @input="changeQuantity"
        />
      </label>
      <p class="mt-2 font-black text-slate-950">
        {{ formatVnd(Number(item.current_price) * item.quantity) }}
      </p>
      <button
        class="mt-2 inline-flex items-center gap-1 text-xs font-bold text-rose-600 hover:text-rose-800"
        type="button"
        @click="emit('remove', item)"
      >
        <TrashIcon class="h-4 w-4" /> Xóa
      </button>
    </div>
  </article>
</template>
