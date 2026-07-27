import type {
  SellerApplication,
  SellerDocument,
  Shop,
  ShopUpdatePayload,
} from '@/features/seller/types'
import { http } from '@/shared/lib/http'
import type { ApiResponse } from '@/shared/types/api'

import type { AdminSeller, SellerApplicationFilters, SellerFilters } from './types'

export const adminSellersApi = {
  listApplications: (filters: SellerApplicationFilters) =>
    http.get<ApiResponse<SellerApplication[]>>('/admin/seller-applications/', {
      params: filters,
    }),
  getApplication: (profileId: number) =>
    http.get<ApiResponse<SellerApplication>>(`/admin/seller-applications/${profileId}/`),
  approveApplication: (profileId: number, reason = '') =>
    http.post<ApiResponse<SellerApplication>>(`/admin/seller-applications/${profileId}/approve/`, {
      reason,
    }),
  rejectApplication: (profileId: number, reason: string) =>
    http.post<ApiResponse<SellerApplication>>(`/admin/seller-applications/${profileId}/reject/`, {
      reason,
    }),
  reviewDocument: (
    documentId: number,
    reviewStatus: SellerDocument['review_status'],
    reason = '',
  ) =>
    http.post<ApiResponse<SellerDocument>>(`/admin/seller-documents/${documentId}/review/`, {
      review_status: reviewStatus,
      reason,
    }),
  listSellers: (filters: SellerFilters) =>
    http.get<ApiResponse<AdminSeller[]>>('/admin/sellers/', { params: filters }),
  updateSellerShop: (userId: number, payload: ShopUpdatePayload) =>
    http.patch<ApiResponse<AdminSeller>>(`/admin/sellers/${userId}/`, payload),
  deleteSeller: (userId: number, reason: string) =>
    http.delete<ApiResponse<null>>(`/admin/sellers/${userId}/`, { data: { reason } }),
  lockShop: (shopId: number, reason: string) =>
    http.post<ApiResponse<Shop>>(`/admin/shops/${shopId}/lock/`, { reason }),
  unlockShop: (shopId: number, reason: string) =>
    http.post<ApiResponse<Shop>>(`/admin/shops/${shopId}/unlock/`, { reason }),
}
