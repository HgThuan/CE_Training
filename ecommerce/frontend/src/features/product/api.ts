import { http } from '@/shared/lib/http'
import type { ApiResponse } from '@/shared/types/api'

import type {
  Brand,
  Category,
  ProductListFilters,
  PublicProductDetail,
  PublicProductListItem,
} from './types'

export const productApi = {
  list: (filters: ProductListFilters) =>
    http.get<ApiResponse<PublicProductListItem[]>>('/products/', { params: filters }),
  detail: (slug: string, shopSlug?: string) =>
    http.get<ApiResponse<PublicProductDetail>>(`/products/${slug}/`, {
      params: { shop_slug: shopSlug },
    }),
  categories: () => http.get<ApiResponse<Category[]>>('/categories/'),
  brands: () =>
    http.get<ApiResponse<Brand[]>>('/brands/', {
      params: { page_size: 100 },
    }),
}
