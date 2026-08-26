import type { FlashSaleItem } from './types'

export function flashSaleAvailableQuantity(item: FlashSaleItem): number {
  const inventoryStock = Math.max(0, item.available_stock ?? 0)
  const remainingQuota = Math.max(0, item.remaining_quota ?? item.quota - item.sold_count)
  return Math.min(inventoryStock, remainingQuota)
}
