import { defineStore } from 'pinia'
import { ref } from 'vue'

import type { PaginationMeta } from '@/shared/types/api'

import { inventoryApi } from './api'
import type {
  InventoryBalance,
  InventoryFilters,
  MovementFilters,
  StockEntry,
  StockEntryPayload,
  StockMovement,
  StockOutEntry,
  StockOutEntryPayload,
} from './types'

const emptyMeta = (): PaginationMeta => ({
  page: 1,
  page_size: 20,
  total_items: 0,
  total_pages: 0,
})

export function isLowStock(balance: InventoryBalance): boolean {
  return balance.available_stock <= balance.low_stock_threshold
}

export const useInventoryStore = defineStore('inventory', () => {
  const inventory = ref<InventoryBalance[]>([])
  const stockEntries = ref<StockEntry[]>([])
  const stockOutEntries = ref<StockOutEntry[]>([])
  const movements = ref<StockMovement[]>([])
  const inventoryMeta = ref(emptyMeta())
  const entryMeta = ref(emptyMeta())
  const outEntryMeta = ref(emptyMeta())
  const movementMeta = ref(emptyMeta())
  const loading = ref(false)

  async function loadInventory(filters: InventoryFilters = {}): Promise<void> {
    loading.value = true
    try {
      const response = await inventoryApi.list(filters)
      inventory.value = response.data.data
      inventoryMeta.value = response.data.meta ?? emptyMeta()
    } finally {
      loading.value = false
    }
  }

  async function loadStockEntries(page = 1): Promise<void> {
    loading.value = true
    try {
      const response = await inventoryApi.stockEntries(page)
      stockEntries.value = response.data.data
      entryMeta.value = response.data.meta ?? emptyMeta()
    } finally {
      loading.value = false
    }
  }

  async function saveStockEntry(
    payload: StockEntryPayload,
    entryId?: number,
  ): Promise<StockEntry> {
    const response = entryId
      ? await inventoryApi.updateStockEntry(entryId, payload)
      : await inventoryApi.createStockEntry(payload)
    await loadStockEntries(entryMeta.value.page)
    return response.data.data
  }

  async function confirmStockEntry(entryId: number): Promise<StockEntry> {
    const response = await inventoryApi.confirmStockEntry(entryId)
    await Promise.all([loadStockEntries(entryMeta.value.page), loadInventory()])
    return response.data.data
  }

  async function loadStockOutEntries(page = 1): Promise<void> {
    loading.value = true
    try {
      const response = await inventoryApi.stockOutEntries(page)
      stockOutEntries.value = response.data.data
      outEntryMeta.value = response.data.meta ?? emptyMeta()
    } finally {
      loading.value = false
    }
  }

  async function saveStockOutEntry(
    payload: StockOutEntryPayload,
    entryId?: number,
  ): Promise<StockOutEntry> {
    const response = entryId
      ? await inventoryApi.updateStockOutEntry(entryId, payload)
      : await inventoryApi.createStockOutEntry(payload)
    await loadStockOutEntries(outEntryMeta.value.page)
    return response.data.data
  }

  async function confirmStockOutEntry(entryId: number): Promise<StockOutEntry> {
    const response = await inventoryApi.confirmStockOutEntry(entryId)
    await Promise.all([loadStockOutEntries(outEntryMeta.value.page), loadInventory()])
    return response.data.data
  }

  async function loadMovements(filters: MovementFilters = {}): Promise<void> {
    loading.value = true
    try {
      const response = await inventoryApi.movements(filters)
      movements.value = response.data.data
      movementMeta.value = response.data.meta ?? emptyMeta()
    } finally {
      loading.value = false
    }
  }

  async function updateThreshold(
    variantId: string,
    lowStockThreshold: number,
  ): Promise<void> {
    await inventoryApi.updateThreshold(variantId, lowStockThreshold)
    await loadInventory()
  }

  return {
    inventory,
    stockEntries,
    stockOutEntries,
    movements,
    inventoryMeta,
    entryMeta,
    outEntryMeta,
    movementMeta,
    loading,
    loadInventory,
    loadStockEntries,
    saveStockEntry,
    confirmStockEntry,
    loadStockOutEntries,
    saveStockOutEntry,
    confirmStockOutEntry,
    loadMovements,
    updateThreshold,
  }
})

