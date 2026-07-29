import { http } from '@/shared/lib/http'
import type { ApiResponse } from '@/shared/types/api'

import type { PublicShopData, PublicShopSort, ShopFollowResult } from './types'

export const shopApi = {
  getPublicShop: (slug: string, page = 1, sort: PublicShopSort = 'newest', pageSize = 12) =>
    http.get<ApiResponse<PublicShopData>>(`/shops/${slug}/`, {
      params: { page, page_size: pageSize, sort },
    }),
  toggleFollow: (shopId: number) =>
    http.post<ApiResponse<ShopFollowResult>>(`/shops/${shopId}/follow/`),
}
