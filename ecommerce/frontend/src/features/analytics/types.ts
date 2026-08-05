export interface Summary {
  revenue: string | number
  orders: number
  customers?: number
  products: number
  pending_orders?: number
  shop_name?: string
}

export interface ChartPoint {
  date: string
  revenue: string | number
  orders: number
}

export interface RankingRow {
  id?: number | string
  customer_id?: number
  product_id?: string
  name?: string
  email?: string
  product_name?: string
  revenue?: string | number
  spending?: string | number
  quantity?: number
  orders?: number
}

export interface SiteSetting {
  key: string
  value: unknown
  value_type: string
  description: string
  is_public: boolean
}

export interface AuditEntry {
  id: number
  actor: string
  action: string
  target_type: string
  target_id: string
  request_id: string
  created_at: string
}
