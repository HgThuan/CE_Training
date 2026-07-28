<script setup lang="ts">
import { computed } from 'vue'

import { formatVnd } from '@/shared/lib/formatters'

import { useVariantSelection } from '../composables/useVariantSelection'
import type { ProductAttribute, ProductVariant } from '../types'

const props = defineProps<{
  attributes: ProductAttribute[]
  variants: ProductVariant[]
}>()

const emit = defineEmits<{
  change: [variant: ProductVariant | null]
}>()

const { selection, selectedVariant, isComplete, select, isAvailable } = useVariantSelection(
  () => props.attributes,
  () => props.variants,
)

const priceLabel = computed(() =>
  selectedVariant.value ? formatVnd(selectedVariant.value.sale_price) : '',
)

function choose(attributeId: string, valueId: string): void {
  select(attributeId, valueId)
  emit('change', selectedVariant.value)
}
</script>

<template>
  <div class="space-y-6">
    <fieldset v-for="attribute in attributes" :key="attribute.id">
      <legend class="flex w-full items-center justify-between text-sm font-bold text-slate-900">
        <span>{{ attribute.name }}</span>
        <span v-if="selection[attribute.id]" class="font-medium text-indigo-600">
          {{
            attribute.values.find((value) => value.id === selection[attribute.id])?.display_value ||
            attribute.values.find((value) => value.id === selection[attribute.id])?.value
          }}
        </span>
      </legend>
      <div class="mt-3 flex flex-wrap gap-2.5">
        <button
          v-for="value in attribute.values"
          :key="value.id"
          class="inline-flex min-h-11 items-center gap-2 rounded-xl border px-4 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400 disabled:line-through"
          :class="
            selection[attribute.id] === value.id
              ? 'border-indigo-600 bg-indigo-50 text-indigo-700 ring-1 ring-indigo-600'
              : 'border-slate-300 bg-white text-slate-700 hover:border-slate-500'
          "
          type="button"
          :disabled="selection[attribute.id] !== value.id && !isAvailable(attribute.id, value.id)"
          @click="choose(attribute.id, value.id)"
        >
          <span
            v-if="attribute.display_type === 'color' && value.color_code"
            class="h-5 w-5 rounded-full border border-black/10"
            :style="{ backgroundColor: value.color_code }"
            aria-hidden="true"
          />
          {{ value.display_value || value.value }}
        </button>
      </div>
    </fieldset>
    <p
      v-if="attributes.length && isComplete && !selectedVariant"
      class="rounded-xl bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-900"
    >
      Tổ hợp này hiện không khả dụng. Vui lòng chọn một lựa chọn khác.
    </p>
    <p v-else-if="selectedVariant" class="text-sm text-slate-600">
      SKU: <strong class="text-slate-900">{{ selectedVariant.sku }}</strong>
      <span class="mx-2 text-slate-300">•</span>
      Giá: <strong class="text-indigo-700">{{ priceLabel }}</strong>
      <span class="mx-2 text-slate-300">•</span>
      Tồn:
      <strong :class="selectedVariant.stock_quantity ? 'text-emerald-700' : 'text-rose-700'">
        {{ selectedVariant.stock_quantity }}
      </strong>
    </p>
  </div>
</template>
