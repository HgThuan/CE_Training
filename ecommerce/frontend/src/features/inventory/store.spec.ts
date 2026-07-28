import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { inventoryApi } from './api'
import { isLowStock, useInventoryStore } from './store'
import type { InventoryBalance } from './types'

vi.mock('./api', () => ({
  inventoryApi: {
    list: vi.fn(),
    stockEntries: vi.fn(),
    createStockEntry: vi.fn(),
    updateStockEntry: vi.fn(),
    confirmStockEntry: vi.fn(),
    stockOutEntries: vi.fn(),
    createStockOutEntry: vi.fn(),
    updateStockOutEntry: vi.fn(),
    confirmStockOutEntry: vi.fn(),
    movements: vi.fn(),
    updateThreshold: vi.fn(),
  },
}))

const balance: InventoryBalance = {
  variant_id: 'variant-1',
  product_id: 'product-1',
  product_name: 'Áo khoác',
  sku: 'AO-DO-M',
  variant_name: 'Đỏ / M',
  available_stock: 5,
  reserved_stock: 2,
  low_stock_threshold: 5,
  is_low_stock: true,
  updated_at: '2026-07-28T00:00:00Z',
}

describe('inventory store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('treats equality with threshold as low stock', () => {
    expect(isLowStock(balance)).toBe(true)
    expect(isLowStock({ ...balance, available_stock: 6 })).toBe(false)
  })

  it('loads balances and pagination metadata', async () => {
    vi.mocked(inventoryApi.list).mockResolvedValue(
      {
        data: {
          success: true,
          message: 'ok',
          data: [balance],
          meta: {
            page: 1,
            page_size: 20,
            total_items: 1,
            total_pages: 1,
          },
        },
      } as never,
    )
    const store = useInventoryStore()

    await store.loadInventory({ low_stock: true })

    expect(inventoryApi.list).toHaveBeenCalledWith({ low_stock: true })
    expect(store.inventory).toEqual([balance])
    expect(store.inventoryMeta.total_items).toBe(1)
  })
})
