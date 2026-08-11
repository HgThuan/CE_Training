import type {
  ProductMedia,
  SellerAttribute,
  SellerAttributePayload,
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
  suspend: (productId: string) =>
    http.post<ApiResponse<SellerProductDetail>>(`/seller/products/${productId}/suspend/`),
  restore: (productId: string) =>
    http.post<ApiResponse<SellerProductDetail>>(`/seller/products/${productId}/restore/`),
  attributes: () =>
    http.get<ApiResponse<SellerAttribute[]>>('/seller/attributes/', {
      params: { page_size: 100 },
    }),
  createAttribute: (payload: SellerAttributePayload) =>
    http.post<ApiResponse<SellerAttribute>>('/seller/attributes/', payload),
  uploadMedia: (
    productId: string,
    file: File,
    mediaType: 'image' | 'video',
    variantId?: string,
  ) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('media_type', mediaType)
    if (variantId) formData.append('variant_id', variantId)
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
  lookupVariantByBarcode: (barcode: string) =>
    http.get<ApiResponse<SellerProductVariant>>('/seller/variants/lookup/', {
      params: { barcode },
    }),
}
