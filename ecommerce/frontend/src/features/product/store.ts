import { defineStore } from 'pinia'
import { ref } from 'vue'

import type { PaginationMeta } from '@/shared/types/api'

import { productApi } from './api'
import type {
  Brand,
  Category,
  ProductListFilters,
  PublicProductDetail,
  PublicProductListItem,
} from './types'

const EMPTY_META: PaginationMeta = {
  page: 1,
  page_size: 20,
  total_items: 0,
  total_pages: 0,
}

export const useProductStore = defineStore('products', () => {
  const products = ref<PublicProductListItem[]>([])
  const detail = ref<PublicProductDetail | null>(null)
  const categories = ref<Category[]>([])
  const brands = ref<Brand[]>([])
  const meta = ref<PaginationMeta>({ ...EMPTY_META })
  const loading = ref(false)
  const catalogLoading = ref(false)
  let detailRequestSequence = 0

  async function loadCatalog(): Promise<void> {
    if (categories.value.length && brands.value.length) return
    catalogLoading.value = true
    try {
      const [categoryResponse, brandResponse] = await Promise.all([
        productApi.categories(),
        productApi.brands(),
      ])
      categories.value = categoryResponse.data.data
      brands.value = brandResponse.data.data
    } finally {
      catalogLoading.value = false
    }
  }

  async function loadProducts(filters: ProductListFilters): Promise<void> {
    loading.value = true
    try {
      const response = await productApi.list(filters)
      products.value = response.data.data
      meta.value = response.data.meta ?? { ...EMPTY_META }
    } finally {
      loading.value = false
    }
  }

  async function loadDetail(slug: string, shopSlug?: string): Promise<void> {
    const sequence = ++detailRequestSequence
    loading.value = true
    detail.value = null
    try {
      const nextDetail = (await productApi.detail(slug, shopSlug)).data.data
      if (sequence === detailRequestSequence) detail.value = nextDetail
    } finally {
      if (sequence === detailRequestSequence) loading.value = false
    }
  }

  return {
    products,
    detail,
    categories,
    brands,
    meta,
    loading,
    catalogLoading,
    loadCatalog,
    loadProducts,
    loadDetail,
  }
})
