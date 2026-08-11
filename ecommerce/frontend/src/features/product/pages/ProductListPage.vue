<script setup lang="ts">
import {
  AdjustmentsHorizontalIcon,
  MagnifyingGlassIcon,
  Squares2X2Icon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'
import { storeToRefs } from 'pinia'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import FormMessage from '@/features/auth/components/FormMessage.vue'
import { getErrorMessage } from '@/features/auth/errors'

import ProductCard from '../components/ProductCard.vue'
import ProductCompareTable from '../components/ProductCompareTable.vue'
import { useCompareStore } from '../compare-store'
import { useProductStore } from '../store'
import type { Category, CategoryOption, ProductListFilters, ProductSort } from '../types'

const route = useRoute()
const router = useRouter()
const productStore = useProductStore()
const compareStore = useCompareStore()
const { comparison, comparing } = storeToRefs(compareStore)

const filters = reactive({
  search: '',
  categoryId: '',
  brandId: '',
  minPrice: '',
  maxPrice: '',
  sort: '-created_at' as ProductSort,
  page: 1,
})
const mobileFiltersOpen = ref(false)
const errorMessage = ref('')

const categoryOptions = computed(() => {
  const options: CategoryOption[] = []
  const visit = (categories: Category[], depth: number): void => {
    for (const category of categories) {
      options.push({ id: category.id, name: category.name, depth })
      visit(category.children, depth + 1)
    }
  }
  visit(productStore.categories, 0)
  return options
})

const activeFilterCount = computed(
  () =>
    [
      filters.categoryId,
      filters.brandId,
      filters.minPrice,
      filters.maxPrice,
      filters.search,
    ].filter(Boolean).length,
)

function hydrateFilters() {
  filters.search = typeof route.query.q === 'string' ? route.query.q : ''
  filters.categoryId = typeof route.query.category === 'string' ? route.query.category : ''
  filters.brandId = typeof route.query.brand === 'string' ? route.query.brand : ''
  filters.minPrice = typeof route.query.min_price === 'string' ? route.query.min_price : ''
  filters.maxPrice = typeof route.query.max_price === 'string' ? route.query.max_price : ''
  filters.sort = (
    typeof route.query.sort === 'string' ? route.query.sort : '-created_at'
  ) as ProductSort
  filters.page = Math.max(Number(route.query.page) || 1, 1)
}

async function loadProducts(): Promise<void> {
  errorMessage.value = ''
  const requestFilters: ProductListFilters = {
    search: filters.search || undefined,
    category_id: filters.categoryId || undefined,
    brand_id: filters.brandId || undefined,
    min_price: filters.minPrice || undefined,
    max_price: filters.maxPrice || undefined,
    sort: filters.sort,
    page: filters.page,
    page_size: 12,
  }
  try {
    await productStore.loadProducts(requestFilters)
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
}

async function syncAndLoad(resetPage = false): Promise<void> {
  if (resetPage) filters.page = 1
  await router.push({
    query: {
      q: filters.search || undefined,
      category: filters.categoryId || undefined,
      brand: filters.brandId || undefined,
      min_price: filters.minPrice || undefined,
      max_price: filters.maxPrice || undefined,
      sort: filters.sort === '-created_at' ? undefined : filters.sort,
      page: filters.page > 1 ? String(filters.page) : undefined,
    },
  })
  mobileFiltersOpen.value = false
}

async function changePage(page: number): Promise<void> {
  if (page < 1 || page > productStore.meta.total_pages || page === filters.page) return
  filters.page = page
  await syncAndLoad()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

async function resetFilters(): Promise<void> {
  Object.assign(filters, {
    search: '',
    categoryId: '',
    brandId: '',
    minPrice: '',
    maxPrice: '',
    sort: '-created_at',
    page: 1,
  })
  await syncAndLoad()
}

watch(
  () => route.query,
  () => {
    hydrateFilters()
    void loadProducts()
  },
  { immediate: true },
)

onMounted(async () => {
  try {
    await productStore.loadCatalog()
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
})
</script>

<template>
  <div class="min-h-screen bg-[#f8fafc] text-slate-900">
    <main class="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:py-12">
      <div class="max-w-3xl">
        <p class="text-sm font-bold uppercase tracking-[0.22em] text-indigo-600">Catalog</p>
        <h1 class="mt-3 text-4xl font-black tracking-tight sm:text-5xl">Tìm món đồ dành cho bạn</h1>
        <p class="mt-4 text-base leading-7 text-slate-600 sm:text-lg">
          Khám phá sản phẩm đã được kiểm duyệt từ các gian hàng trên toàn hệ thống.
        </p>
      </div>

      <form class="mt-8 flex gap-3" role="search" @submit.prevent="syncAndLoad(true)">
        <label class="relative flex-1">
          <span class="sr-only">Tìm kiếm sản phẩm</span>
          <MagnifyingGlassIcon
            class="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400"
          />
          <input
            v-model.trim="filters.search"
            class="h-14 w-full rounded-2xl border border-slate-300 bg-white pl-12 pr-4 outline-none transition focus:border-indigo-600 focus:ring-4 focus:ring-indigo-100"
            placeholder="Tìm theo tên sản phẩm…"
          />
        </label>
        <button
          class="hidden rounded-2xl bg-slate-950 px-7 font-bold text-white transition hover:bg-indigo-700 sm:block"
        >
          Tìm kiếm
        </button>
        <button
          class="relative grid h-14 w-14 place-items-center rounded-2xl border border-slate-300 bg-white lg:hidden"
          type="button"
          aria-label="Mở bộ lọc"
          @click="mobileFiltersOpen = true"
        >
          <AdjustmentsHorizontalIcon class="h-6 w-6" />
          <span
            v-if="activeFilterCount"
            class="absolute -right-1 -top-1 grid h-5 min-w-5 place-items-center rounded-full bg-indigo-600 px-1 text-[10px] font-bold text-white"
          >
            {{ activeFilterCount }}
          </span>
        </button>
      </form>

      <FormMessage v-if="errorMessage" class="mt-6" :message="errorMessage" />

      <div class="mt-10 grid gap-8 lg:grid-cols-[260px_1fr]">
        <div
          v-if="mobileFiltersOpen"
          class="fixed inset-0 z-40 bg-slate-950/40 backdrop-blur-sm lg:hidden"
          @click="mobileFiltersOpen = false"
        />
        <aside
          class="fixed inset-y-0 right-0 z-50 w-[min(88vw,360px)] overflow-y-auto bg-white p-6 shadow-2xl transition lg:sticky lg:top-6 lg:z-auto lg:block lg:h-fit lg:w-auto lg:rounded-3xl lg:p-5 lg:shadow-sm lg:ring-1 lg:ring-slate-200"
          :class="mobileFiltersOpen ? 'translate-x-0' : 'translate-x-full lg:translate-x-0'"
          aria-label="Bộ lọc sản phẩm"
        >
          <div class="flex items-center justify-between">
            <h2 class="font-black">Bộ lọc</h2>
            <button
              class="grid h-9 w-9 place-items-center rounded-xl bg-slate-100 lg:hidden"
              type="button"
              aria-label="Đóng bộ lọc"
              @click="mobileFiltersOpen = false"
            >
              <XMarkIcon class="h-5 w-5" />
            </button>
          </div>

          <form class="mt-6 space-y-6" @submit.prevent="syncAndLoad(true)">
            <label class="block">
              <span class="text-sm font-bold">Danh mục</span>
              <select
                v-model="filters.categoryId"
                class="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5"
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
                v-model="filters.brandId"
                class="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5"
              >
                <option value="">Tất cả thương hiệu</option>
                <option v-for="brand in productStore.brands" :key="brand.id" :value="brand.id">
                  {{ brand.name }}
                </option>
              </select>
            </label>

            <fieldset>
              <legend class="text-sm font-bold">Khoảng giá</legend>
              <div class="mt-2 grid grid-cols-2 gap-2">
                <input
                  v-model="filters.minPrice"
                  class="min-w-0 rounded-xl border border-slate-300 px-3 py-2.5"
                  type="number"
                  min="0"
                  step="1000"
                  placeholder="Từ"
                  aria-label="Giá tối thiểu"
                />
                <input
                  v-model="filters.maxPrice"
                  class="min-w-0 rounded-xl border border-slate-300 px-3 py-2.5"
                  type="number"
                  min="0"
                  step="1000"
                  placeholder="Đến"
                  aria-label="Giá tối đa"
                />
              </div>
            </fieldset>

            <button class="w-full rounded-xl bg-indigo-600 px-4 py-3 font-bold text-white">
              Áp dụng
            </button>
            <button
              v-if="activeFilterCount"
              class="w-full text-sm font-bold text-slate-500 hover:text-slate-950"
              type="button"
              @click="resetFilters"
            >
              Xóa bộ lọc
            </button>
          </form>
        </aside>

        <section aria-live="polite">
          <div class="flex flex-wrap items-center justify-between gap-4">
            <div class="flex items-center gap-3">
              <Squares2X2Icon class="h-5 w-5 text-slate-500" />
              <p class="text-sm text-slate-600">
                <strong class="text-slate-950">{{ productStore.meta.total_items }}</strong> sản phẩm
              </p>
            </div>
            <label class="flex items-center gap-3 text-sm font-semibold">
              <span class="hidden text-slate-500 sm:inline">Sắp xếp</span>
              <select
                v-model="filters.sort"
                class="rounded-xl border border-slate-300 bg-white px-3 py-2.5"
                @change="syncAndLoad(true)"
              >
                <option value="-created_at">Mới nhất</option>
                <option value="price">Giá thấp đến cao</option>
                <option value="-price">Giá cao đến thấp</option>
                <option value="-sold_count">Bán chạy</option>
                <option value="-rating">Đánh giá tốt</option>
              </select>
            </label>
          </div>

          <div
            v-if="comparing"
            id="product-comparison-result"
            class="mt-6 animate-pulse overflow-hidden rounded-3xl bg-white p-6 ring-1 ring-slate-200"
            aria-label="Đang tạo bảng so sánh"
          >
            <div class="h-6 w-40 rounded bg-slate-200" />
            <div class="mt-6 space-y-4">
              <div v-for="index in 4" :key="index" class="h-12 rounded-xl bg-slate-100" />
            </div>
          </div>
          <div v-else-if="comparison" id="product-comparison-result" class="scroll-mt-24">
            <ProductCompareTable :comparison="comparison" />
          </div>

          <div
            v-if="productStore.loading"
            class="mt-6 grid gap-5 sm:grid-cols-2 xl:grid-cols-3"
            aria-label="Đang tải sản phẩm"
          >
            <div
              v-for="index in 6"
              :key="index"
              class="overflow-hidden rounded-3xl bg-white ring-1 ring-slate-200"
            >
              <div class="aspect-[4/3] animate-pulse bg-slate-200" />
              <div class="space-y-3 p-5">
                <div class="h-3 w-1/3 animate-pulse rounded bg-slate-200" />
                <div class="h-5 animate-pulse rounded bg-slate-200" />
                <div class="h-5 w-2/3 animate-pulse rounded bg-slate-200" />
              </div>
            </div>
          </div>

          <div
            v-else-if="productStore.products.length"
            class="mt-6 grid gap-5 sm:grid-cols-2 xl:grid-cols-3"
          >
            <ProductCard
              v-for="product in productStore.products"
              :key="product.id"
              :product="product"
            />
          </div>

          <div
            v-else
            class="mt-6 rounded-3xl border border-dashed border-slate-300 bg-white px-6 py-16 text-center"
          >
            <MagnifyingGlassIcon class="mx-auto h-10 w-10 text-slate-400" />
            <h2 class="mt-4 text-xl font-black">Chưa tìm thấy sản phẩm</h2>
            <p class="mt-2 text-slate-600">Thử đổi từ khóa hoặc nới rộng bộ lọc của bạn.</p>
            <button
              class="mt-6 rounded-xl bg-slate-950 px-5 py-3 font-bold text-white"
              type="button"
              @click="resetFilters"
            >
              Xóa bộ lọc
            </button>
          </div>

          <nav
            v-if="productStore.meta.total_pages > 1"
            class="mt-10 flex items-center justify-center gap-2"
            aria-label="Phân trang"
          >
            <button
              class="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold disabled:opacity-40"
              :disabled="filters.page === 1"
              @click="changePage(filters.page - 1)"
            >
              Trước
            </button>
            <span class="px-3 text-sm text-slate-600">
              Trang <strong>{{ filters.page }}</strong> / {{ productStore.meta.total_pages }}
            </span>
            <button
              class="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold disabled:opacity-40"
              :disabled="filters.page === productStore.meta.total_pages"
              @click="changePage(filters.page + 1)"
            >
              Sau
            </button>
          </nav>
        </section>
      </div>
    </main>
  </div>
</template>
