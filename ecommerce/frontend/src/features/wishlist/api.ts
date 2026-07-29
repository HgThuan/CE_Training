import { http } from '@/shared/lib/http'
import type { ApiResponse } from '@/shared/types/api'

import type { WishlistItem, WishlistListParams, WishlistToggleResult } from './types'

export const wishlistApi = {
  list: (params: WishlistListParams = {}) =>
    http.get<ApiResponse<WishlistItem[]>>('/wishlist/', { params }),
  toggle: (productId: string) =>
    http.post<ApiResponse<WishlistToggleResult>>('/wishlist/toggle/', {
      product_id: productId,
    }),
}
