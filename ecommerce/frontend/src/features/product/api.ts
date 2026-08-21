import { http } from '@/shared/lib/http'
import type { ApiResponse } from '@/shared/types/api'

import type {
  Brand,
  Category,
  CreateQuestionPayload,
  ProductAIReviewSummary,
  ProductAISummary,
  ProductCompareData,
  ProductListFilters,
  ProductQuestion,
  ProductRecommendationData,
  PublicProductDetail,
  PublicProductListItem,
  QuestionListParams,
} from './types'

function browsingHistoryParams(browsingHistory: string[]): { browsing_history?: string } {
  const serializedHistory = browsingHistory.join(',')
  return serializedHistory ? { browsing_history: serializedHistory } : {}
}

function recommendationParams(
  browsingHistory: string[],
  cartProducts: string[],
  landingContext: 'home' | 'product_detail',
) {
  return {
    ...browsingHistoryParams(browsingHistory),
    cart_products: cartProducts.length ? cartProducts.join(',') : undefined,
    landing_context: landingContext,
  }
}

export const productApi = {
  list: (filters: ProductListFilters) =>
    http.get<ApiResponse<PublicProductListItem[]>>('/products/', { params: filters }),
  detail: (slug: string, shopSlug?: string) =>
    http.get<ApiResponse<PublicProductDetail>>(`/products/${slug}/`, {
      params: { shop_slug: shopSlug },
    }),
  similar: (productId: string) =>
    http.get<ApiResponse<ProductRecommendationData>>(`/products/${productId}/similar/`),
  recommendations: (
    productId: string,
    browsingHistory: string[] = [],
    cartProducts: string[] = [],
  ) =>
    http.get<ApiResponse<ProductRecommendationData>>(`/products/${productId}/recommendations/`, {
      params: recommendationParams(browsingHistory, cartProducts, 'product_detail'),
    }),
  homeRecommendations: (browsingHistory: string[] = []) =>
    http.get<ApiResponse<ProductRecommendationData>>('/ai/recommendations/', {
      params: recommendationParams(browsingHistory, [], 'home'),
    }),
  aiReviewSummary: (productId: string) =>
    http.get<ApiResponse<ProductAIReviewSummary>>(`/ai/products/${productId}/ai-review-summary`),
  aiSummary: (productId: string) =>
    http.get<ApiResponse<ProductAISummary>>(`/ai/products/${productId}/ai-summary`),
  compareProducts: (productIds: string[]) =>
    http.post<ApiResponse<ProductCompareData>>('/products/compare', {
      product_ids: productIds,
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
