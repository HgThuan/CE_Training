import { http } from '@/shared/lib/http'
import type { ApiResponse } from '@/shared/types/api'

import type {
  Brand,
  Category,
  CreateQuestionPayload,
  ProductListFilters,
  ProductQuestion,
  PublicProductDetail,
  PublicProductListItem,
  QuestionListParams,
} from './types'

export const productApi = {
  list: (filters: ProductListFilters) =>
    http.get<ApiResponse<PublicProductListItem[]>>('/products/', { params: filters }),
  detail: (slug: string, shopSlug?: string) =>
    http.get<ApiResponse<PublicProductDetail>>(`/products/${slug}/`, {
      params: { shop_slug: shopSlug },
    }),
  listQuestions: (productId: string, params: QuestionListParams = {}) =>
    http.get<ApiResponse<ProductQuestion[]>>(`/products/${productId}/questions/`, {
      params,
    }),
  createQuestion: (productId: string, payload: CreateQuestionPayload) =>
    http.post<ApiResponse<ProductQuestion>>(`/products/${productId}/questions/`, payload),
  categories: () => http.get<ApiResponse<Category[]>>('/categories/'),
  brands: () =>
    http.get<ApiResponse<Brand[]>>('/brands/', {
      params: { page_size: 100 },
    }),
}
