import type {
  ProductMedia,
  SellerAttribute,
  SellerProductDetail,
  SellerProductFilters,
  SellerProductListItem,
  SellerProductPayload,
  SellerProductVariant,
  VariantUpdatePayload,
} from '@/features/product/types'
import { http } from '@/shared/lib/http'
import type { ApiResponse } from '@/shared/types/api'

export const sellerProductApi = {
  list: (filters: SellerProductFilters) =>
    http.get<ApiResponse<SellerProductListItem[]>>('/seller/products/', { params: filters }),
  detail: (productId: string) =>
    http.get<ApiResponse<SellerProductDetail>>(`/seller/products/${productId}/`),
  create: (payload: SellerProductPayload) =>
    http.post<ApiResponse<SellerProductDetail>>('/seller/products/', payload),
  update: (productId: string, payload: SellerProductPayload) =>
    http.patch<ApiResponse<SellerProductDetail>>(`/seller/products/${productId}/`, payload),
  delete: (productId: string) =>
    http.delete<ApiResponse<{ id: string; is_deleted: boolean }>>(`/seller/products/${productId}/`),
  submit: (productId: string) =>
    http.post<ApiResponse<SellerProductDetail>>(`/seller/products/${productId}/submit/`),
  attributes: () =>
    http.get<ApiResponse<SellerAttribute[]>>('/seller/attributes/', {
      params: { page_size: 100 },
    }),
  uploadMedia: (productId: string, file: File, mediaType: 'image' | 'video') => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('media_type', mediaType)
    return http.post<ApiResponse<ProductMedia>>(`/seller/products/${productId}/media/`, formData)
  },
  deleteMedia: (productId: string, mediaId: string) =>
    http.delete<ApiResponse<{ id: string; is_deleted: boolean }>>(
      `/seller/products/${productId}/media/${mediaId}/`,
    ),
  reorderMedia: (productId: string, orderedIds: string[]) =>
    http.post<ApiResponse<SellerProductDetail>>(`/seller/products/${productId}/media/reorder/`, {
      ordered_ids: orderedIds,
    }),
  generateVariants: (productId: string, attributeValueIds: string[]) =>
    http.post<ApiResponse<SellerProductVariant[]>>(
      `/seller/products/${productId}/variants/generate/`,
      { attribute_value_ids: attributeValueIds },
    ),
  updateVariant: (productId: string, variantId: string, payload: VariantUpdatePayload) =>
    http.patch<ApiResponse<SellerProductVariant>>(
      `/seller/products/${productId}/variants/${variantId}/`,
      payload,
    ),
}
