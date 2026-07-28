import type { PaginationMeta } from '@/shared/types/api'

export type StockDocumentStatus = 'draft' | 'confirmed'
export type StockOutEntryType = 'out' | 'adjustment'
export type StockBucket = 'available' | 'reserved'
export type StockMovementType = 'in' | 'out' | 'adjustment' | 'reserve' | 'release' | 'commit'
export type StockReferenceType = 'stock_entry' | 'stock_out' | 'adjustment' | 'order'

export interface InventoryBalance {
  variant_id: string
  product_id: string
  product_name: string
  sku: string
  variant_name: string | null
  available_stock: number
  reserved_stock: number
  low_stock_threshold: number
  is_low_stock: boolean
  updated_at: string
}

export interface StockEntryItem {
  id: number
  variant_id: string
  product_name: string
  sku: string
  quantity: number
  unit_cost: string
}

export interface StockEntry {
  id: number
  supplier_name: string
  status: StockDocumentStatus
  note: string
  items: StockEntryItem[]
  created_by: string
  confirmed_by: string | null
  confirmed_at: string | null
  created_at: string
  updated_at: string
}

export interface StockEntryPayload {
  supplier_name: string
  note?: string
  items: Array<{
    variant_id: string
    quantity: number
    unit_cost: string
  }>
}

export interface StockOutEntryItem {
  id: number
  variant_id: string
  product_name: string
  sku: string
  quantity: number
}

export interface StockOutEntry {
  id: number
  entry_type: StockOutEntryType
  reason: string
  status: StockDocumentStatus
  items: StockOutEntryItem[]
  created_by: string
  confirmed_by: string | null
  confirmed_at: string | null
  created_at: string
  updated_at: string
}

export interface StockOutEntryPayload {
  entry_type: StockOutEntryType
  reason: string
  items: Array<{
    variant_id: string
    quantity: number
  }>
}

export interface StockMovement {
  id: number
  variant_id: string
  product_name: string
  sku: string
  movement_type: StockMovementType
  bucket: StockBucket
  quantity: number
  balance_after: number
  reference_type: StockReferenceType
  reference_id: string
  note: string
  created_by: string
  created_at: string
}

export interface InventoryFilters {
  low_stock?: boolean
  page?: number
  page_size?: number
}

export interface MovementFilters {
  variant_id?: string
  date_from?: string
  date_to?: string
  page?: number
  page_size?: number
}

export interface InventoryStateMeta {
  inventory: PaginationMeta
  entries: PaginationMeta
  outEntries: PaginationMeta
  movements: PaginationMeta
}
