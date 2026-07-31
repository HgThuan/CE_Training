import { http } from '@/shared/lib/http'
import type { ApiResponse } from '@/shared/types/api'

import type { FlashSale, FlashSalePayload, Voucher, VoucherPayload } from './types'

export const promotionApi = {
  listAdminVouchers: () => http.get<ApiResponse<Voucher[]>>('/admin/vouchers'),
  createAdminVoucher: (payload: VoucherPayload) =>
    http.post<ApiResponse<Voucher>>('/admin/vouchers', payload),
  updateAdminVoucher: (id: string, payload: Partial<VoucherPayload>) =>
    http.patch<ApiResponse<Voucher>>(`/admin/vouchers/${id}`, payload),
  deleteAdminVoucher: (id: string) => http.delete<ApiResponse<null>>(`/admin/vouchers/${id}`),
  listSellerVouchers: () => http.get<ApiResponse<Voucher[]>>('/seller/vouchers'),
  createSellerVoucher: (payload: VoucherPayload) =>
    http.post<ApiResponse<Voucher>>('/seller/vouchers', payload),
  updateSellerVoucher: (id: string, payload: Partial<VoucherPayload>) =>
    http.patch<ApiResponse<Voucher>>(`/seller/vouchers/${id}`, payload),
  deleteSellerVoucher: (id: string) => http.delete<ApiResponse<null>>(`/seller/vouchers/${id}`),
  availableVouchers: () => http.get<ApiResponse<Voucher[]>>('/customer/vouchers/available'),
  listAdminFlashSales: () => http.get<ApiResponse<FlashSale[]>>('/admin/flash-sales'),
  createFlashSale: (payload: FlashSalePayload) =>
    http.post<ApiResponse<FlashSale>>('/admin/flash-sales', payload),
  updateFlashSale: (id: string, payload: Partial<FlashSalePayload>) =>
    http.patch<ApiResponse<FlashSale>>(`/admin/flash-sales/${id}`, payload),
  deleteFlashSale: (id: string) => http.delete<ApiResponse<null>>(`/admin/flash-sales/${id}`),
  activeFlashSales: () => http.get<ApiResponse<FlashSale[]>>('/flash-sales/active'),
}
