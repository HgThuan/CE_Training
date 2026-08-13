import { http } from '@/shared/lib/http'
import type { ApiResponse } from '@/shared/types/api'

import type { CartData, CartPreviewPayload, GuestCartItem, PreviewResult } from './types'

export const cartApi = {
  getCart: () => http.get<ApiResponse<CartData>>('/cart/'),
  addItem: (variantId: string, quantity: number) =>
    http.post<ApiResponse<CartData>>('/cart/items', {
      variant_id: variantId,
      quantity,
    }),
  updateItem: (itemId: string, payload: { quantity?: number; is_selected?: boolean }) =>
    http.patch<ApiResponse<CartData>>(`/cart/items/${itemId}`, payload),
  removeItem: (itemId: string) => http.delete<ApiResponse<CartData>>(`/cart/items/${itemId}`),
  mergeGuestCart: (items: GuestCartItem[]) =>
    http.post<ApiResponse<CartData>>('/cart/merge', {
      items: items.map(({ variant_id, quantity }) => ({ variant_id, quantity })),
    }),
  previewCheckout: (payload: CartPreviewPayload) =>
    http.post<ApiResponse<PreviewResult>>('/cart/preview', payload),
}
