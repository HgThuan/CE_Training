import { http } from '@/shared/lib/http'
import type { ApiResponse } from '@/shared/types/api'

import type {
  Dispute,
  ReturnRequest,
  Review,
  ReviewReport,
  SellerCustomer,
  SellerCustomerOrder,
} from './types'

export const afterSalesApi = {
  productReviews: (productId: string) =>
    http.get<ApiResponse<Review[]>>(`/products/${productId}/reviews`),
  createReview: (orderItemId: string, payload: Record<string, unknown>) =>
    http.post<ApiResponse<Review>>(`/order-items/${orderItemId}/review`, payload),
  updateReview: (reviewId: string, payload: Record<string, unknown>) =>
    http.patch<ApiResponse<Review>>(`/reviews/${reviewId}`, payload),
  createReturn: (orderId: string, payload: Record<string, unknown>) =>
    http.post<ApiResponse<ReturnRequest>>(`/orders/${orderId}/return-request`, payload),
  orderReturns: (orderId: string) =>
    http.get<ApiResponse<ReturnRequest[]>>(`/orders/${orderId}/return-request`),
  escalateReturn: (returnId: string) =>
    http.post<ApiResponse<Dispute>>(`/return-requests/${returnId}/escalate`, {}),
  sellerCustomers: (search = '') =>
    http.get<ApiResponse<SellerCustomer[]>>('/seller/customers', { params: { search } }),
  sellerCustomerOrders: (customerId: number) =>
    http.get<ApiResponse<SellerCustomerOrder[]>>(`/seller/customers/${customerId}/orders`),
  sellerReviews: (params: Record<string, string> = {}) =>
    http.get<ApiResponse<Review[]>>('/seller/reviews', { params }),
  replyReview: (reviewId: string, content: string) =>
    http.post<ApiResponse<Review>>(`/seller/reviews/${reviewId}/reply`, { content }),
  reportReview: (reviewId: string, reasonDetail: string) =>
    http.post(`/seller/reviews/${reviewId}/report`, {
      reason_code: 'INAPPROPRIATE',
      reason_detail: reasonDetail,
    }),
  sellerReturns: (status = '') =>
    http.get<ApiResponse<ReturnRequest[]>>('/seller/return-requests', { params: { status } }),
  decideReturn: (returnId: string, action: 'APPROVE' | 'REJECT', response: string) =>
    http.post<ApiResponse<ReturnRequest>>(`/seller/return-requests/${returnId}/decision`, {
      action,
      response,
    }),
  adminDisputes: (status = '') =>
    http.get<ApiResponse<Dispute[]>>('/admin/disputes', { params: { status } }),
  reviewDispute: (id: string) =>
    http.post<ApiResponse<Dispute>>(`/admin/disputes/${id}/review`, {}),
  resolveDispute: (id: string, payload: Record<string, unknown>) =>
    http.post<ApiResponse<Dispute>>(`/admin/disputes/${id}/resolve`, payload),
  reviewReports: () => http.get<ApiResponse<ReviewReport[]>>('/admin/review-reports'),
  resolveReviewReport: (id: string, action: 'HIDE' | 'KEEP', note: string) =>
    http.post<ApiResponse<ReviewReport>>(`/admin/review-reports/${id}/resolve`, {
      action,
      note,
    }),
}
