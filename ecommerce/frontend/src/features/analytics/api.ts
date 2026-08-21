import { http } from '@/shared/lib/http'
import type { ApiResponse } from '@/shared/types/api'

import type {
  AuditEntry,
  ChatbotMetrics,
  RankingRow,
  RevenueChartResponse,
  SiteSetting,
  Summary,
} from './types'

export const analyticsApi = {
  adminSummary: (days: number) =>
    http.get<ApiResponse<Summary>>('/admin/dashboard/summary/', { params: { days } }),
  adminRevenue: (days: number, period: string = 'day') =>
    http.get<ApiResponse<RevenueChartResponse>>('/admin/dashboard/revenue-chart/', {
      params: { days, period },
    }),
  adminProducts: (days: number) =>
    http.get<ApiResponse<RankingRow[]>>('/admin/dashboard/top-products/', { params: { days } }),
  chatbotMetrics: (days: number) =>
    http.get<ApiResponse<ChatbotMetrics>>('/admin/dashboard/chatbot', { params: { days } }),
  sellerSummary: (days: number) =>
    http.get<ApiResponse<Summary>>('/seller/dashboard/summary/', { params: { days } }),
  sellerRevenue: (days: number, period: string = 'day') =>
    http.get<ApiResponse<RevenueChartResponse>>('/seller/dashboard/revenue-chart/', {
      params: { days, period },
    }),
  sellerProducts: (days: number) =>
    http.get<ApiResponse<RankingRow[]>>('/seller/dashboard/top-products/', { params: { days } }),
  ranking: (kind: 'top-sellers' | 'top-customers' | 'top-categories', days: number) =>
    http.get<ApiResponse<RankingRow[]>>(`/admin/reports/${kind}/`, { params: { days } }),
  rates: (days: number) =>
    http.get<ApiResponse<Record<string, number>>>('/admin/reports/cancel-return-rate/', {
      params: { days },
    }),
  auditLogs: (params?: {
    action?: string
    target_type?: string
    target_id?: string
    request_id?: string
    page?: number
    page_size?: number
  }) => http.get<ApiResponse<AuditEntry[]>>('/admin/audit-logs/', { params }),
  settings: () => http.get<ApiResponse<SiteSetting[]>>('/admin/settings/'),
  updateSettings: (settings: SiteSetting[]) =>
    http.put<ApiResponse<SiteSetting[]>>('/admin/settings/', { settings }),
  exportUrl: '/admin/reports/export/',
}
