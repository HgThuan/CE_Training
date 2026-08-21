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

export interface RevenueChartResponse {
  current_revenue: number
  prior_revenue: number
  growth: number
  chart: ChartPoint[]
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
  reason?: string
  diff?: Record<string, unknown>
  request_id: string
  created_at: string
}

export interface ChatbotMetrics {
  sessions: number
  handoffs: number
  handoff_rate: number
  automated_resolution_rate: number
  average_response_ms: number
  feedback_count: number
  feedback_rate: number
  csat: number
  resolved_feedback: number
  unresolved_feedback: number
  variants: Array<{
    experiment_variant: string
    sessions: number
    escalated: number
    feedback_count: number
    csat: number
    handoff_rate: number
  }>
}
