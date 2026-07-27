import { http } from '@/shared/lib/http'
import type { ApiResponse } from '@/shared/types/api'

import type {
  SellerApplication,
  SellerApplicationPayload,
  SellerDocument,
  Shop,
  ShopUpdatePayload,
} from './types'

export const sellerApi = {
  getApplication: () => http.get<ApiResponse<SellerApplication | null>>('/seller-applications/me/'),
  submitApplication: (payload: SellerApplicationPayload) =>
    http.post<ApiResponse<SellerApplication>>('/seller-applications/me/', payload),
  uploadDocument: (documentType: SellerDocument['document_type'], document: File) => {
    const formData = new FormData()
    formData.append('document_type', documentType)
    formData.append('document', document)
    return http.post<ApiResponse<SellerDocument>>('/seller-applications/me/documents/', formData)
  },
  getShop: () => http.get<ApiResponse<Shop>>('/seller/shop/'),
  updateShop: (payload: ShopUpdatePayload) =>
    http.patch<ApiResponse<Shop>>('/seller/shop/', payload),
  uploadShopImage: (imageType: 'logo' | 'cover', image: File) => {
    const formData = new FormData()
    formData.append('image', image)
    return http.post<ApiResponse<Shop>>(`/seller/shop/${imageType}/`, formData)
  },
}
