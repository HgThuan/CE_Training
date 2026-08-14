import { http } from '@/shared/lib/http'
import type { ApiResponse } from '@/shared/types/api'

import type { CheckoutPreview, CommerceOrder, ShopOrder } from './types'

export const orderApi = {
  preview: (payload: Record<string, unknown>) =>
    http.post<ApiResponse<CheckoutPreview>>('/checkout/preview', payload),
  confirm: (payload: Record<string, unknown>, idempotencyKey: string) =>
    http.post<ApiResponse<CommerceOrder & { payment_redirect_url?: string }>>(
      '/checkout/confirm',
      payload,
      { headers: { 'Idempotency-Key': idempotencyKey } },
    ),
  customerOrders: (status?: string) =>
    http.get<ApiResponse<CommerceOrder[]>>('/orders', { params: { status } }),
  customerOrder: (id: string) => http.get<ApiResponse<CommerceOrder>>(`/orders/${id}`),
  cancel: (orderId: string, shopOrderId: string, reasonCode = 'CUSTOMER_CHANGED_MIND') =>
    http.post<ApiResponse<CommerceOrder>>(`/orders/${orderId}/cancel`, {
      shop_order_id: shopOrderId,
      reason_code: reasonCode,
    }),
  reorder: (orderId: string) => http.post(`/orders/${orderId}/reorder`, {}),
  initiatePayment: (orderId: string) =>
    http.post<ApiResponse<{ payment_url: string }>>(`/payment/${orderId}/initiate`, {}),
  sellerOrders: (status?: string) =>
    http.get<ApiResponse<ShopOrder[]>>('/seller/orders', { params: { status } }),
  sellerAction: (shopOrderId: string, action: string, reason = '') =>
    http.post<ApiResponse<ShopOrder>>(`/seller/orders/${shopOrderId}/${action}`, {
      reason,
      reason_code: 'SELLER_OPERATION',
    }),
  packingSlip: (shopOrderId: string) =>
    http.get<string>(`/seller/orders/${shopOrderId}/packing-slip`, { responseType: 'text' }),
  adminOrders: (params: Record<string, string | number>) =>
    http.get<ApiResponse<CommerceOrder[]>>('/admin/orders', { params }),
  adminOrder: (orderId: string) => http.get<ApiResponse<CommerceOrder>>(`/admin/orders/${orderId}`),
  paymentStatus: (orderId: string) => http.get(`/payment/${orderId}/status`),
  verifyVnpayReturn: (params: Record<string, string>) =>
    http.get('/payment/callback/vnpay', { params }),
}
