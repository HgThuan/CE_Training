import type {
  SellerApplication,
  SellerDocument,
  Shop,
  ShopUpdatePayload,
} from '@/features/seller/types'
import { axiosClient } from '@/shared/lib/http'
import type { ApiResponse } from '@/shared/types/api'

import type { AdminSeller, SellerApplicationFilters, SellerFilters } from './types'

export const adminSellersApi = {
  listApplications: (filters: SellerApplicationFilters) =>
    axiosClient.get<ApiResponse<SellerApplication[]>>('/admin/seller-applications/', {
      params: filters,
    }),
  getApplication: (profileId: number) =>
    axiosClient.get<ApiResponse<SellerApplication>>(`/admin/seller-applications/${profileId}/`),
  approveApplication: (profileId: number, reason = '') =>
    axiosClient.post<ApiResponse<SellerApplication>>(
      `/admin/seller-applications/${profileId}/approve/`,
      { reason },
    ),
  rejectApplication: (profileId: number, reason: string) =>
    axiosClient.post<ApiResponse<SellerApplication>>(
      `/admin/seller-applications/${profileId}/reject/`,
      { reason },
    ),
  reviewDocument: (
    documentId: number,
    reviewStatus: SellerDocument['review_status'],
    reason = '',
  ) =>
    axiosClient.post<ApiResponse<SellerDocument>>(`/admin/seller-documents/${documentId}/review/`, {
      review_status: reviewStatus,
      reason,
    }),
  listSellers: (filters: SellerFilters) =>
    axiosClient.get<ApiResponse<AdminSeller[]>>('/admin/sellers/', { params: filters }),
  updateSellerShop: (userId: number, payload: ShopUpdatePayload) =>
    axiosClient.patch<ApiResponse<AdminSeller>>(`/admin/sellers/${userId}/`, payload),
  deleteSeller: (userId: number, reason: string) =>
    axiosClient.delete<ApiResponse<null>>(`/admin/sellers/${userId}/`, { data: { reason } }),
  lockShop: (shopId: number, reason: string) =>
    axiosClient.post<ApiResponse<Shop>>(`/admin/shops/${shopId}/lock/`, { reason }),
  unlockShop: (shopId: number, reason: string) =>
    axiosClient.post<ApiResponse<Shop>>(`/admin/shops/${shopId}/unlock/`, { reason }),
}
