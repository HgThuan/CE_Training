<script setup lang="ts">
import { computed, reactive, watch } from 'vue'

import type { Brand, Category, CategoryOption } from '@/features/product/types'

import type { SearchFilterModel } from '../types'

const props = defineProps<{
  modelValue: SearchFilterModel
  categories: Category[]
  brands: Brand[]
  disabled?: boolean
}>()

const emit = defineEmits<{
  apply: [filters: SearchFilterModel]
  reset: []
}>()

const draft = reactive<SearchFilterModel>({ ...props.modelValue })

const categoryOptions = computed(() => {
  const options: CategoryOption[] = []
  const visit = (categories: Category[], depth: number): void => {
    for (const category of categories) {
      options.push({ id: category.id, name: category.name, depth })
      visit(category.children, depth + 1)
    }
  }
  visit(props.categories, 0)
  return options
})

watch(
  () => props.modelValue,
  (value) => Object.assign(draft, value),
  { deep: true },
)

function applyFilters(): void {
  emit('apply', { ...draft })
}

function resetFilters(): void {
  Object.assign(draft, {
    category: '',
    brand: '',
    priceMin: '',
    priceMax: '',
    ratingMin: '',
    inStock: false,
    shop: '',
  })
  emit('reset')
}
</script>

<template>
  <form class="space-y-6" aria-label="Bộ lọc tìm kiếm" @submit.prevent="applyFilters">
    <label class="block">
      <span class="text-sm font-bold">Danh mục</span>
      <select
        v-model="draft.category"
        class="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5"
        :disabled="disabled"
      >
        <option value="">Tất cả danh mục</option>
        <option v-for="category in categoryOptions" :key="category.id" :value="category.id">
          {{ `${'— '.repeat(category.depth)}${category.name}` }}
        </option>
      </select>
    </label>

    <label class="block">
      <span class="text-sm font-bold">Thương hiệu</span>
      <select
        v-model="draft.brand"
        class="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5"
        :disabled="disabled"
      >
        <option value="">Tất cả thương hiệu</option>
        <option v-for="brand in brands" :key="brand.id" :value="brand.id">
          {{ brand.name }}
        </option>
      </select>
    </label>

    <fieldset>
      <legend class="text-sm font-bold">Khoảng giá</legend>
      <div class="mt-2 grid grid-cols-2 gap-2">
        <input
          v-model="draft.priceMin"
          class="min-w-0 rounded-xl border border-slate-300 px-3 py-2.5"
          type="number"
          min="0"
          step="1000"
          placeholder="Từ"
          aria-label="Giá tối thiểu"
          :disabled="disabled"
        />
        <input
          v-model="draft.priceMax"
          class="min-w-0 rounded-xl border border-slate-300 px-3 py-2.5"
          type="number"
          min="0"
          step="1000"
          placeholder="Đến"
          aria-label="Giá tối đa"
          :disabled="disabled"
        />
      </div>
    </fieldset>

    <label class="block">
      <span class="text-sm font-bold">Đánh giá tối thiểu</span>
      <select
        v-model="draft.ratingMin"
        class="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5"
        :disabled="disabled"
      >
        <option value="">Tất cả đánh giá</option>
        <option value="4">4 sao trở lên</option>
        <option value="3">3 sao trở lên</option>
        <option value="2">2 sao trở lên</option>
        <option value="1">1 sao trở lên</option>
      </select>
    </label>

    <label class="block">
      <span class="text-sm font-bold">Gian hàng</span>
      <input
        v-model.trim="draft.shop"
        class="mt-2 w-full rounded-xl border border-slate-300 px-3 py-2.5"
        placeholder="Tên hoặc slug gian hàng"
        :disabled="disabled"
      />
    </label>

    <label class="flex items-center gap-3 text-sm font-bold">
      <input
        v-model="draft.inStock"
        class="h-5 w-5 rounded accent-indigo-600"
        type="checkbox"
        :disabled="disabled"
      />
      Chỉ sản phẩm còn hàng
    </label>

    <button
      class="w-full rounded-xl bg-indigo-600 px-4 py-3 font-bold text-white hover:bg-indigo-700 disabled:opacity-50"
      :disabled="disabled"
    >
      Áp dụng bộ lọc
    </button>
    <button
      class="w-full text-sm font-bold text-slate-500 hover:text-slate-950 disabled:opacity-50"
      type="button"
      :disabled="disabled"
      @click="resetFilters"
    >
      Xóa bộ lọc
    </button>
  </form>
</template>
