import { http } from '@/shared/lib/http'
import type { ApiResponse } from '@/shared/types/api'

import type { AuditEntry, ChartPoint, RankingRow, SiteSetting, Summary } from './types'

export const analyticsApi = {
  adminSummary: (days: number) => http.get<ApiResponse<Summary>>('/admin/dashboard/summary/', { params: { days } }),
  adminRevenue: (days: number) => http.get<ApiResponse<ChartPoint[]>>('/admin/dashboard/revenue-chart/', { params: { days } }),
  adminProducts: (days: number) => http.get<ApiResponse<RankingRow[]>>('/admin/dashboard/top-products/', { params: { days } }),
  sellerSummary: (days: number) => http.get<ApiResponse<Summary>>('/seller/dashboard/summary/', { params: { days } }),
  sellerRevenue: (days: number) => http.get<ApiResponse<ChartPoint[]>>('/seller/dashboard/revenue-chart/', { params: { days } }),
  sellerProducts: (days: number) => http.get<ApiResponse<RankingRow[]>>('/seller/dashboard/top-products/', { params: { days } }),
  ranking: (kind: 'top-sellers' | 'top-customers' | 'top-categories', days: number) => http.get<ApiResponse<RankingRow[]>>(`/admin/reports/${kind}/`, { params: { days } }),
  rates: (days: number) => http.get<ApiResponse<Record<string, number>>>('/admin/reports/cancel-return-rate/', { params: { days } }),
  auditLogs: () => http.get<ApiResponse<AuditEntry[]>>('/admin/audit-logs/'),
  settings: () => http.get<ApiResponse<SiteSetting[]>>('/admin/settings/'),
  updateSettings: (settings: SiteSetting[]) => http.put<ApiResponse<SiteSetting[]>>('/admin/settings/', { settings }),
  exportUrl: '/admin/reports/export/',
}
