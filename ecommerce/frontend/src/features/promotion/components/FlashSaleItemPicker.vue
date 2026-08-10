<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { productApi } from '@/features/product/api'
import type { Category, CategoryOption } from '@/features/product/types'
import { formatVnd } from '@/shared/lib/formatters'

import { promotionApi } from '../api'
import type { FlashSaleCatalogVariant, FlashSaleItem } from '../types'

type SelectionMode = 'products' | 'category' | 'all'

const props = defineProps<{ items: FlashSaleItem[] }>()
const emit = defineEmits<{ 'update:items': [items: FlashSaleItem[]] }>()

const mode = ref<SelectionMode>('products')
const search = ref('')
const categoryId = ref('')
const categories = ref<CategoryOption[]>([])
const catalog = ref<FlashSaleCatalogVariant[]>([])
const loading = ref(false)
const adding = ref(false)
const error = ref('')
const selectionModes: Array<{ value: SelectionMode; label: string }> = [
  { value: 'products', label: 'Chọn sản phẩm' },
  { value: 'category', label: 'Theo danh mục' },
  { value: 'all', label: 'Toàn sàn' },
]

const groupedProducts = computed(() => {
  const groups = new Map<
    string,
    {
      id: string
      name: string
      shop: string
      image: string | null
      variants: FlashSaleCatalogVariant[]
    }
  >()
  for (const variant of catalog.value) {
    const group = groups.get(variant.product_id)
    if (group) group.variants.push(variant)
    else
      groups.set(variant.product_id, {
        id: variant.product_id,
        name: variant.product_name,
        shop: variant.shop_name,
        image: variant.primary_image,
        variants: [variant],
      })
  }
  return [...groups.values()]
})

function flattenCategories(source: Category[]): CategoryOption[] {
  const result: CategoryOption[] = []
  const visit = (items: Category[], depth: number): void => {
    for (const item of items) {
      result.push({ id: item.id, name: item.name, depth })
      visit(item.children ?? [], depth + 1)
    }
  }
  visit(source, 0)
  return result
}

async function loadCatalog(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const response = await promotionApi.flashSaleCatalog({
      page: 1,
      page_size: 100,
      search: search.value.trim() || undefined,
      category_id: mode.value === 'category' ? categoryId.value || undefined : undefined,
    })
    catalog.value = response.data.data
  } catch {
    error.value = 'Không thể tải danh sách sản phẩm. Vui lòng thử lại.'
  } finally {
    loading.value = false
  }
}

async function loadAllMatching(): Promise<FlashSaleCatalogVariant[]> {
  const variants: FlashSaleCatalogVariant[] = []
  let page = 1
  let totalPages = 1
  do {
    const response = await promotionApi.flashSaleCatalog({
      page,
      page_size: 100,
      category_id: mode.value === 'category' ? categoryId.value : undefined,
    })
    variants.push(...response.data.data)
    totalPages = response.data.meta?.total_pages ?? 1
    page += 1
  } while (page <= totalPages)
  return variants
}

function asItem(variant: FlashSaleCatalogVariant): FlashSaleItem {
  return {
    variant: variant.id,
    product_id: variant.product_id,
    product_name: variant.product_name,
    variant_sku: variant.sku,
    shop_id: variant.shop_id,
    shop_name: variant.shop_name,
    primary_image: variant.primary_image,
    original_price: variant.sale_price,
    sale_price: variant.sale_price,
    quota: Math.max(1, Math.min(variant.available_stock, 10)),
    sold_count: 0,
    category_id: variant.category_id,
    category_name: variant.category_name,
    available_stock: variant.available_stock,
  }
}

function addVariants(variants: FlashSaleCatalogVariant[]): void {
  const existing = new Set(props.items.map((item) => item.variant))
  const additions = variants.filter((variant) => !existing.has(variant.id)).map(asItem)
  emit('update:items', [...props.items, ...additions])
}

async function addScope(): Promise<void> {
  if (mode.value === 'category' && !categoryId.value) {
    error.value = 'Hãy chọn một danh mục.'
    return
  }
  adding.value = true
  error.value = ''
  try {
    addVariants(await loadAllMatching())
  } catch {
    error.value = 'Không thể thêm sản phẩm. Vui lòng thử lại.'
  } finally {
    adding.value = false
  }
}

function update(index: number, field: 'sale_price' | 'quota', value: string | number): void {
  emit(
    'update:items',
    props.items.map((item, position) => (position === index ? { ...item, [field]: value } : item)),
  )
}

function remove(index: number): void {
  emit(
    'update:items',
    props.items.filter((_, position) => position !== index),
  )
}

function changeMode(value: SelectionMode): void {
  mode.value = value
  catalog.value = []
  error.value = ''
}

onMounted(async () => {
  try {
    categories.value = flattenCategories((await productApi.categories()).data.data)
  } catch {
    error.value = 'Không thể tải danh mục sản phẩm.'
  }
  await loadCatalog()
})
</script>

<template>
  <fieldset class="space-y-4">
    <legend class="text-sm font-black">Chọn sản phẩm tham gia</legend>

    <div class="grid gap-2 rounded-2xl bg-slate-50 p-2 sm:grid-cols-3">
      <button
        v-for="option in selectionModes"
        :key="option.value"
        type="button"
        class="rounded-xl px-3 py-2 text-sm font-bold"
        :class="mode === option.value ? 'bg-indigo-600 text-white' : 'bg-white text-slate-700'"
        @click="changeMode(option.value)"
      >
        {{ option.label }}
      </button>
    </div>

    <div v-if="mode === 'products'" class="rounded-2xl border p-4">
      <div class="flex gap-2">
        <input
          v-model="search"
          class="min-w-0 flex-1 rounded-xl border px-3 py-2"
          placeholder="Tìm theo tên sản phẩm, SKU hoặc gian hàng"
          @keyup.enter="loadCatalog"
        />
        <button
          type="button"
          class="rounded-xl bg-slate-900 px-4 py-2 font-bold text-white"
          @click="loadCatalog"
        >
          Tìm
        </button>
      </div>
      <p v-if="loading" class="mt-4 text-sm text-slate-500">Đang tải sản phẩm...</p>
      <div v-else class="mt-4 max-h-72 space-y-2 overflow-y-auto">
        <article
          v-for="product in groupedProducts"
          :key="product.id"
          class="flex items-center gap-3 rounded-xl bg-slate-50 p-3"
        >
          <img
            v-if="product.image"
            :src="product.image"
            :alt="product.name"
            class="h-12 w-12 rounded-lg object-cover"
          />
          <div v-else class="grid h-12 w-12 place-items-center rounded-lg bg-slate-200 text-xs">
            Ảnh
          </div>
          <div class="min-w-0 flex-1">
            <p class="truncate font-bold">{{ product.name }}</p>
            <p class="text-xs text-slate-500">
              {{ product.shop }} · {{ product.variants.length }} biến thể
            </p>
            <p class="truncate text-xs text-slate-500">
              {{
                product.variants
                  .map((variant) =>
                    variant.name ? `${variant.name} (${variant.sku})` : variant.sku,
                  )
                  .join(', ')
              }}
            </p>
          </div>
          <button
            type="button"
            class="rounded-lg border border-indigo-300 px-3 py-2 text-xs font-bold text-indigo-700"
            @click="addVariants(product.variants)"
          >
            Thêm sản phẩm
          </button>
        </article>
        <p v-if="!groupedProducts.length" class="py-4 text-center text-sm text-slate-500">
          Không tìm thấy sản phẩm phù hợp.
        </p>
      </div>
    </div>

    <div v-else-if="mode === 'category'" class="rounded-2xl border p-4">
      <label class="block text-sm font-bold">
        Danh mục
        <select
          v-model="categoryId"
          class="mt-1 w-full rounded-xl border px-3 py-2"
          @change="loadCatalog"
        >
          <option value="">-- Chọn danh mục --</option>
          <option v-for="category in categories" :key="category.id" :value="category.id">
            {{ '— '.repeat(category.depth) }}{{ category.name }}
          </option>
        </select>
      </label>
      <p class="mt-2 text-sm text-slate-500">
        {{ loading ? 'Đang kiểm tra...' : `${catalog.length} biến thể trong trang xem trước` }}
      </p>
      <button
        type="button"
        :disabled="adding || !categoryId"
        class="mt-3 rounded-xl bg-indigo-600 px-4 py-2 font-bold text-white disabled:opacity-50"
        @click="addScope"
      >
        {{ adding ? 'Đang thêm...' : 'Thêm toàn bộ danh mục' }}
      </button>
    </div>

    <div v-else class="rounded-2xl border border-amber-200 bg-amber-50 p-4">
      <p class="font-bold text-amber-900">Áp dụng cho toàn bộ sản phẩm đủ điều kiện trên sàn</p>
      <p class="mt-1 text-sm text-amber-800">
        Chỉ sản phẩm đã duyệt, biến thể đang hoạt động và còn tồn kho mới được thêm.
      </p>
      <button
        type="button"
        :disabled="adding"
        class="mt-3 rounded-xl bg-amber-700 px-4 py-2 font-bold text-white disabled:opacity-50"
        @click="addScope"
      >
        {{ adding ? 'Đang thêm...' : 'Thêm tất cả sản phẩm trên sàn' }}
      </button>
    </div>

    <p v-if="error" class="rounded-xl bg-rose-50 px-3 py-2 text-sm font-bold text-rose-700">
      {{ error }}
    </p>

    <div class="flex items-center justify-between">
      <p class="text-sm font-black">Đã chọn {{ items.length }} biến thể</p>
      <button
        v-if="items.length"
        type="button"
        class="text-sm font-bold text-rose-700"
        @click="
          emit(
            'update:items',
            items.filter((item) => item.sold_count > 0),
          )
        "
      >
        Bỏ các mục chưa bán
      </button>
    </div>

    <div
      v-for="(item, index) in items"
      :key="item.id ?? item.variant"
      class="grid gap-3 rounded-2xl bg-slate-50 p-4 sm:grid-cols-[minmax(0,1fr)_150px_110px_auto]"
    >
      <div class="min-w-0">
        <p class="truncate text-sm font-black">{{ item.product_name || 'Sản phẩm' }}</p>
        <p class="truncate text-xs text-slate-500">
          {{ item.variant_sku || 'Biến thể'
          }}<span v-if="item.shop_name"> · {{ item.shop_name }}</span>
        </p>
        <p v-if="item.available_stock !== undefined" class="mt-1 text-xs text-emerald-700">
          Còn {{ item.available_stock }} sản phẩm · Giá hiện tại
          {{ formatVnd(item.original_price || 0) }}
        </p>
      </div>
      <label class="text-xs font-bold">
        Giá Flash Sale
        <input
          :value="item.sale_price"
          type="number"
          min="0"
          :max="item.original_price"
          class="mt-1 w-full rounded-xl border px-3 py-2"
          :disabled="item.sold_count > 0"
          @input="update(index, 'sale_price', ($event.target as HTMLInputElement).value)"
        />
      </label>
      <label class="text-xs font-bold">
        Số lượng
        <input
          :value="item.quota"
          type="number"
          min="1"
          :max="item.available_stock"
          class="mt-1 w-full rounded-xl border px-3 py-2"
          :disabled="item.sold_count > 0"
          @input="update(index, 'quota', Number(($event.target as HTMLInputElement).value))"
        />
      </label>
      <button
        type="button"
        class="self-end rounded-xl px-3 py-2 font-bold text-rose-700 disabled:opacity-40"
        :disabled="item.sold_count > 0"
        @click="remove(index)"
      >
        Xóa
      </button>
      <p v-if="item.sold_count > 0" class="text-xs text-amber-700 sm:col-span-4">
        Đã bán {{ item.sold_count }} sản phẩm; giá và số lượng được khóa trên giao diện.
      </p>
    </div>
  </fieldset>
</template>
