import { describe, expect, it } from 'vitest'

import { flashSaleAvailableQuantity } from './availability'
import type { FlashSaleItem } from './types'

function item(overrides: Partial<FlashSaleItem> = {}): FlashSaleItem {
  return {
    variant: 'variant-1',
    sale_price: '80000',
    quota: 10,
    sold_count: 2,
    remaining_quota: 8,
    available_stock: 7,
    ...overrides,
  }
}

describe('flashSaleAvailableQuantity', () => {
  it('uses the lower value between inventory and remaining quota', () => {
    expect(flashSaleAvailableQuantity(item())).toBe(7)
    expect(flashSaleAvailableQuantity(item({ available_stock: 20 }))).toBe(8)
  })

  it('treats missing or exhausted inventory as unavailable', () => {
    expect(flashSaleAvailableQuantity(item({ available_stock: 0 }))).toBe(0)
    expect(flashSaleAvailableQuantity(item({ available_stock: undefined }))).toBe(0)
  })
})
