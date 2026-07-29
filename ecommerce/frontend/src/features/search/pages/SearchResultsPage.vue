<script setup lang="ts">
import {
  AdjustmentsHorizontalIcon,
  MagnifyingGlassIcon,
  Squares2X2Icon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import FormMessage from '@/features/auth/components/FormMessage.vue'
import { getErrorMessage } from '@/features/auth/errors'
import ProductCard from '@/features/product/components/ProductCard.vue'
import { useProductStore } from '@/features/product/store'
import type { PublicProductListItem } from '@/features/product/types'
import type { PaginationMeta } from '@/shared/types/api'

import { searchApi } from '../api'
import FilterSidebar from '../components/FilterSidebar.vue'
import SortDropdown from '../components/SortDropdown.vue'
import type { SearchFilterModel, SearchParams, SearchSort } from '../types'

const route = useRoute()
const router = useRouter()
const productStore = useProductStore()
const products = ref<PublicProductListItem[]>([])
const meta = ref<PaginationMeta>({
  page: 1,
  page_size: 12,
  total_items: 0,
  total_pages: 0,
})
const loading = ref(true)
const errorMessage = ref('')
const mobileFiltersOpen = ref(false)
const sort = ref<SearchSort | ''>('')
const filters = reactive<SearchFilterModel>({
  category: '',
  brand: '',
  priceMin: '',
  priceMax: '',
  ratingMin: '',
  inStock: false,
  shop: '',
})
let requestSequence = 0

const searchTerm = computed(() => (typeof route.query.q === 'string' ? route.query.q.trim() : ''))
const activeFilterCount = computed(
  () =>
    [
      filters.category,
      filters.brand,
      filters.priceMin,
      filters.priceMax,
      filters.ratingMin,
      filters.inStock,
      filters.shop,
    ].filter(Boolean).length,
)

function routeString(name: string): string {
  const value = route.query[name]
  return typeof value === 'string' ? value : ''
}

function hydrateFromRoute(): void {
  Object.assign(filters, {
    category: routeString('category'),
    brand: routeString('brand'),
    priceMin: routeString('price_min'),
    priceMax: routeString('price_max'),
    ratingMin: routeString('rating_min'),
    inStock: ['true', '1'].includes(routeString('in_stock')),
    shop: routeString('shop'),
  })
  const routeSort = routeString('sort')
  sort.value = ['-created_at', 'price', '-price', '-avg_rating', '-sold_count'].includes(routeSort)
    ? (routeSort as SearchSort)
    : ''
}

function requestParams(): SearchParams {
  return {
    q: searchTerm.value,
    category: filters.category || undefined,
    brand: filters.brand || undefined,
    price_min: filters.priceMin || undefined,
    price_max: filters.priceMax || undefined,
    rating_min: filters.ratingMin ? Number(filters.ratingMin) : undefined,
    in_stock: filters.inStock || undefined,
    shop: filters.shop || undefined,
    sort: sort.value || undefined,
    page: Math.max(Number(route.query.page) || 1, 1),
    page_size: 12,
  }
}

async function loadResults(): Promise<void> {
  const sequence = ++requestSequence
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await searchApi.search(requestParams())
    if (sequence !== requestSequence) return
    products.value = response.data.data
    meta.value =
      response.data.meta ??
      ({
        page: 1,
        page_size: products.value.length,
        total_items: products.value.length,
        total_pages: products.value.length ? 1 : 0,
      } satisfies PaginationMeta)
  } catch (error) {
    if (sequence === requestSequence) errorMessage.value = getErrorMessage(error)
  } finally {
    if (sequence === requestSequence) loading.value = false
  }
}

function queryForFilters(
  nextFilters: SearchFilterModel,
  nextSort: SearchSort | '' = sort.value,
  page = 1,
) {
  return {
    q: searchTerm.value || undefined,
    category: nextFilters.category || undefined,
    brand: nextFilters.brand || undefined,
    price_min: nextFilters.priceMin || undefined,
    price_max: nextFilters.priceMax || undefined,
    rating_min: nextFilters.ratingMin || undefined,
    in_stock: nextFilters.inStock ? 'true' : undefined,
    shop: nextFilters.shop || undefined,
    sort: nextSort || undefined,
    page: page > 1 ? String(page) : undefined,
  }
}

async function applyFilters(nextFilters: SearchFilterModel): Promise<void> {
  mobileFiltersOpen.value = false
  await router.push({ path: '/search', query: queryForFilters(nextFilters) })
}

async function resetFilters(): Promise<void> {
  const emptyFilters: SearchFilterModel = {
    category: '',
    brand: '',
    priceMin: '',
    priceMax: '',
    ratingMin: '',
    inStock: false,
    shop: '',
  }
  mobileFiltersOpen.value = false
  await router.push({ path: '/search', query: queryForFilters(emptyFilters) })
}

async function changeSort(nextSort: SearchSort | ''): Promise<void> {
  await router.push({ path: '/search', query: queryForFilters({ ...filters }, nextSort) })
}

async function changePage(page: number): Promise<void> {
  if (page < 1 || page > meta.value.total_pages || page === meta.value.page) return
  await router.push({
    path: '/search',
    query: queryForFilters({ ...filters }, sort.value, page),
  })
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function handleEscape(event: KeyboardEvent): void {
  if (event.key === 'Escape') mobileFiltersOpen.value = false
}

watch(
  () => route.fullPath,
  () => {
    hydrateFromRoute()
    void loadResults()
  },
  { immediate: true },
)

watch(mobileFiltersOpen, (open) => {
  document.body.style.overflow = open ? 'hidden' : ''
})

onMounted(async () => {
  window.addEventListener('keydown', handleEscape)
  try {
    await productStore.loadCatalog()
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
})

onBeforeUnmount(() => {
  requestSequence += 1
  document.body.style.overflow = ''
  window.removeEventListener('keydown', handleEscape)
})
</script>

<template>
  <main class="mx-auto min-h-[70vh] max-w-7xl px-4 py-8 sm:px-6 lg:py-12">
    <div class="flex flex-wrap items-end justify-between gap-5">
      <div>
        <p class="text-sm font-bold uppercase tracking-[0.2em] text-indigo-600">
          Tìm kiếm & khám phá
        </p>
        <h1 class="mt-2 text-3xl font-black tracking-tight sm:text-4xl">
          {{ searchTerm ? `Kết quả cho “${searchTerm}”` : 'Tất cả sản phẩm' }}
        </h1>
        <p class="mt-3 text-slate-600">
          Lọc theo danh mục, thương hiệu, giá, đánh giá và tình trạng tồn kho.
        </p>
      </div>
      <button
        class="relative inline-flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm font-bold lg:hidden"
        type="button"
        @click="mobileFiltersOpen = true"
      >
        <AdjustmentsHorizontalIcon class="h-5 w-5" />
        Bộ lọc
        <span
          v-if="activeFilterCount"
          class="grid h-5 min-w-5 place-items-center rounded-full bg-indigo-600 px-1 text-[10px] text-white"
        >
          {{ activeFilterCount }}
        </span>
      </button>
    </div>

    <FormMessage v-if="errorMessage" class="mt-6" :message="errorMessage" />
    <button
      v-if="errorMessage"
      class="mt-3 text-sm font-bold text-indigo-700"
      type="button"
      @click="loadResults"
    >
      Thử tải lại
    </button>

    <div class="mt-10 grid gap-8 lg:grid-cols-[270px_1fr]">
      <div
        v-if="mobileFiltersOpen"
        class="fixed inset-0 z-40 bg-slate-950/45 backdrop-blur-sm lg:hidden"
        @click="mobileFiltersOpen = false"
      />
      <aside
        class="fixed inset-y-0 right-0 z-50 w-[min(90vw,380px)] overflow-y-auto bg-white p-6 shadow-2xl transition lg:sticky lg:top-24 lg:z-auto lg:block lg:h-fit lg:w-auto lg:rounded-3xl lg:p-5 lg:shadow-sm lg:ring-1 lg:ring-slate-200"
        :class="mobileFiltersOpen ? 'translate-x-0' : 'translate-x-full lg:translate-x-0'"
        aria-label="Bộ lọc tìm kiếm"
      >
        <div class="mb-6 flex items-center justify-between lg:hidden">
          <h2 class="font-black">Bộ lọc</h2>
          <button
            class="grid h-10 w-10 place-items-center rounded-xl bg-slate-100"
            type="button"
            aria-label="Đóng bộ lọc"
            @click="mobileFiltersOpen = false"
          >
            <XMarkIcon class="h-5 w-5" />
          </button>
        </div>
        <FilterSidebar
          :model-value="{ ...filters }"
          :categories="productStore.categories"
          :brands="productStore.brands"
          :disabled="productStore.catalogLoading"
          @apply="applyFilters"
          @reset="resetFilters"
        />
      </aside>

      <section aria-live="polite">
        <div class="flex flex-wrap items-center justify-between gap-4">
          <div class="flex items-center gap-3">
            <Squares2X2Icon class="h-5 w-5 text-slate-500" />
            <p class="text-sm text-slate-600">
              <strong class="text-slate-950">{{ meta.total_items }}</strong> sản phẩm
            </p>
          </div>
          <SortDropdown :model-value="sort" @update:model-value="changeSort" />
        </div>

        <div
          v-if="loading"
          class="mt-6 grid gap-5 sm:grid-cols-2 xl:grid-cols-3"
          aria-label="Đang tải kết quả"
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

        <div v-else-if="products.length" class="mt-6 grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
          <ProductCard v-for="product in products" :key="product.id" :product="product" />
        </div>

        <div
          v-else
          class="mt-6 rounded-3xl border border-dashed border-slate-300 bg-white px-6 py-16 text-center"
        >
          <MagnifyingGlassIcon class="mx-auto h-10 w-10 text-slate-400" />
          <h2 class="mt-4 text-xl font-black">Không tìm thấy sản phẩm</h2>
          <p class="mt-2 text-slate-600">Thử từ khóa khác hoặc nới rộng bộ lọc của bạn.</p>
          <button
            v-if="activeFilterCount"
            class="mt-6 rounded-xl bg-slate-950 px-5 py-3 font-bold text-white"
            type="button"
            @click="resetFilters"
          >
            Xóa bộ lọc
          </button>
        </div>

        <nav
          v-if="meta.total_pages > 1"
          class="mt-10 flex items-center justify-center gap-2"
          aria-label="Phân trang kết quả"
        >
          <button
            class="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold disabled:opacity-40"
            :disabled="meta.page <= 1"
            @click="changePage(meta.page - 1)"
          >
            Trước
          </button>
          <span class="px-3 text-sm text-slate-600">
            Trang <strong>{{ meta.page }}</strong> / {{ meta.total_pages }}
          </span>
          <button
            class="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold disabled:opacity-40"
            :disabled="meta.page >= meta.total_pages"
            @click="changePage(meta.page + 1)"
          >
            Sau
          </button>
        </nav>
      </section>
    </div>
  </main>
</template>
