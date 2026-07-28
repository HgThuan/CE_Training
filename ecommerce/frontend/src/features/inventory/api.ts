import { http } from '@/shared/lib/http'
import type { ApiResponse } from '@/shared/types/api'

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

export const inventoryApi = {
  list: (filters: InventoryFilters = {}) =>
    http.get<ApiResponse<InventoryBalance[]>>('/seller/inventory/', { params: filters }),
  movements: (filters: MovementFilters = {}) =>
    http.get<ApiResponse<StockMovement[]>>('/seller/inventory/movements/', {
      params: filters,
    }),
  stockEntries: (page = 1) =>
    http.get<ApiResponse<StockEntry[]>>('/seller/inventory/stock-entries/', {
      params: { page },
    }),
  createStockEntry: (payload: StockEntryPayload) =>
    http.post<ApiResponse<StockEntry>>('/seller/inventory/stock-entries/', payload),
  updateStockEntry: (entryId: number, payload: Partial<StockEntryPayload>) =>
    http.patch<ApiResponse<StockEntry>>(`/seller/inventory/stock-entries/${entryId}/`, payload),
  confirmStockEntry: (entryId: number) =>
    http.post<ApiResponse<StockEntry>>(`/seller/inventory/stock-entries/${entryId}/confirm/`),
  stockOutEntries: (page = 1) =>
    http.get<ApiResponse<StockOutEntry[]>>('/seller/inventory/stock-out-entries/', {
      params: { page },
    }),
  createStockOutEntry: (payload: StockOutEntryPayload) =>
    http.post<ApiResponse<StockOutEntry>>('/seller/inventory/stock-out-entries/', payload),
  updateStockOutEntry: (entryId: number, payload: Partial<StockOutEntryPayload>) =>
    http.patch<ApiResponse<StockOutEntry>>(
      `/seller/inventory/stock-out-entries/${entryId}/`,
      payload,
    ),
  confirmStockOutEntry: (entryId: number) =>
    http.post<ApiResponse<StockOutEntry>>(
      `/seller/inventory/stock-out-entries/${entryId}/confirm/`,
    ),
  updateThreshold: (variantId: string, lowStockThreshold: number) =>
    http.post<ApiResponse<InventoryBalance>>(`/seller/inventory/${variantId}/threshold/`, {
      low_stock_threshold: lowStockThreshold,
    }),
  joinWaitlist: (variantId: string) =>
    http.post<ApiResponse<{ id: number; variant_id: string; is_notified: boolean }>>(
      `/customer/products/${variantId}/waitlist/`,
    ),
}
