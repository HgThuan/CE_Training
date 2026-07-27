import { http } from '@/shared/lib/http'
import type { ApiResponse } from '@/shared/types/api'

import type { PublicShopData } from './types'

export const shopApi = {
  getPublicShop: (slug: string, page = 1, sort = 'newest') =>
    http.get<ApiResponse<PublicShopData>>(`/shops/${slug}/`, {
      params: { page, sort },
    }),
}
