import { http } from '@/shared/lib/http'
import type { ApiResponse } from '@/shared/types/api'

import type {
  CheckoutVoucherList,
  FlashSale,
  FlashSaleCatalogVariant,
  FlashSalePayload,
  UserVoucher,
  UserVoucherStatus,
  Voucher,
  VoucherPayload,
} from './types'
import type { PreviewResult } from '@/features/cart/types'

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
  voucherCenter: () => http.get<ApiResponse<Voucher[]>>('/voucher-center'),
  collectVoucher: (campaignId: string, idempotencyKey: string) =>
    http.post<ApiResponse<UserVoucher>>(
      `/vouchers/${campaignId}/collect`,
      { idempotency_key: idempotencyKey },
      { headers: { 'Idempotency-Key': idempotencyKey } },
    ),
  myVouchers: (status?: UserVoucherStatus) =>
    http.get<ApiResponse<UserVoucher[]>>('/me/vouchers', { params: { status } }),
  checkoutVouchers: (selectedItemIds: string[]) =>
    http.get<ApiResponse<CheckoutVoucherList>>('/checkout/available-vouchers', {
      params: { selected_item_ids: selectedItemIds.join(',') },
    }),
  applyOwnedVouchers: (payload: {
    user_voucher_ids: string[]
    selected_item_ids: string[]
    checkout_token?: string
  }) =>
    http.post<ApiResponse<PreviewResult & { checkout_token: string; pending_expires_at: string }>>(
      '/checkout/apply-voucher',
      payload,
    ),
  applyVoucherByCode: (payload: {
    code: string
    idempotency_key: string
    selected_item_ids: string[]
    checkout_token?: string
  }) =>
    http.post<ApiResponse<PreviewResult & { checkout_token: string; pending_expires_at: string }>>(
      '/checkout/apply-voucher-by-code',
      payload,
    ),
  shopVouchers: (shopId: number) => http.get<ApiResponse<Voucher[]>>(`/shops/${shopId}/vouchers`),
  listAdminFlashSales: () => http.get<ApiResponse<FlashSale[]>>('/admin/flash-sales'),
  flashSaleCatalog: (params: {
    page?: number
    page_size?: number
    category_id?: string
    search?: string
  }) => http.get<ApiResponse<FlashSaleCatalogVariant[]>>('/admin/flash-sales/catalog', { params }),
  createFlashSale: (payload: FlashSalePayload) =>
    http.post<ApiResponse<FlashSale>>('/admin/flash-sales', payload),
  updateFlashSale: (id: string, payload: Partial<FlashSalePayload>) =>
    http.patch<ApiResponse<FlashSale>>(`/admin/flash-sales/${id}`, payload),
  deleteFlashSale: (id: string) => http.delete<ApiResponse<null>>(`/admin/flash-sales/${id}`),
  activeFlashSales: () => http.get<ApiResponse<FlashSale[]>>('/flash-sales/active'),
}
