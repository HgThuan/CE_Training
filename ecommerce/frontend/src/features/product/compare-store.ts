import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { getErrorMessage } from '@/features/auth/errors'

import { productApi } from './api'
import type { ProductCompareData, PublicProductListItem } from './types'

export const MAX_COMPARE_PRODUCTS = 4
export const MIN_COMPARE_PRODUCTS = 2

export const useCompareStore = defineStore('product-compare', () => {
  const selectedProductIds = ref<string[]>([])
  const selectedProducts = ref<PublicProductListItem[]>([])
  const comparison = ref<ProductCompareData | null>(null)
  const comparing = ref(false)
  const error = ref('')

  const canCompare = computed(
    () => selectedProductIds.value.length >= MIN_COMPARE_PRODUCTS && !comparing.value,
  )
  const isFull = computed(() => selectedProductIds.value.length >= MAX_COMPARE_PRODUCTS)

  function isSelected(productId: string): boolean {
    return selectedProductIds.value.includes(productId)
  }

  function remove(productId: string): void {
    selectedProductIds.value = selectedProductIds.value.filter((id) => id !== productId)
    selectedProducts.value = selectedProducts.value.filter((product) => product.id !== productId)
    comparison.value = null
    error.value = ''
  }

  function toggle(product: PublicProductListItem): boolean {
    if (isSelected(product.id)) {
      remove(product.id)
      return false
    }
    if (isFull.value) return false
    selectedProductIds.value = [...selectedProductIds.value, product.id]
    selectedProducts.value = [...selectedProducts.value, product]
    comparison.value = null
    error.value = ''
    return true
  }

  function clear(): void {
    selectedProductIds.value = []
    selectedProducts.value = []
    comparison.value = null
    error.value = ''
  }

  async function compare(): Promise<boolean> {
    if (!canCompare.value) return false
    comparing.value = true
    comparison.value = null
    error.value = ''
    try {
      comparison.value = (await productApi.compareProducts(selectedProductIds.value)).data.data
      return true
    } catch (reason) {
      error.value = getErrorMessage(reason)
      return false
    } finally {
      comparing.value = false
    }
  }

  return {
    selectedProductIds,
    selectedProducts,
    comparison,
    comparing,
    error,
    canCompare,
    isFull,
    isSelected,
    toggle,
    remove,
    clear,
    compare,
  }
})
