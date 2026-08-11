import type {
  AdminProductListItem,
  Brand,
  BrandPayload,
  Category,
  CategoryPayload,
} from '@/features/product/types'
import type { ProductStatus } from '@/features/product/types'
import { http } from '@/shared/lib/http'
import type { ApiResponse } from '@/shared/types/api'

export const adminCatalogApi = {
  products: (params: {
    page?: number
    page_size?: number
    status?: ProductStatus
    search?: string
  }) => http.get<ApiResponse<AdminProductListItem[]>>('/admin/products/', { params }),
  pendingProducts: (page = 1) =>
    http.get<ApiResponse<AdminProductListItem[]>>('/admin/products/pending/', {
      params: { page, page_size: 20 },
    }),
  approveProduct: (productId: string) =>
    http.post<ApiResponse<AdminProductListItem>>(`/admin/products/${productId}/approve/`),
  rejectProduct: (productId: string, rejectionReason: string) =>
    http.post<ApiResponse<AdminProductListItem>>(`/admin/products/${productId}/reject/`, {
      rejection_reason: rejectionReason,
    }),
  hideProduct: (productId: string) =>
    http.post<ApiResponse<AdminProductListItem>>(`/admin/products/${productId}/hide/`),
  deleteProduct: (productId: string) =>
    http.delete<ApiResponse<{ id: string; is_deleted: boolean }>>(`/admin/products/${productId}/`),

  categories: () =>
    http.get<ApiResponse<Category[]>>('/admin/categories/', {
      params: { page_size: 100 },
    }),
  createCategory: (payload: CategoryPayload) =>
    http.post<ApiResponse<Category>>('/admin/categories/', payload),
  updateCategory: (categoryId: string, payload: Partial<CategoryPayload>) =>
    http.patch<ApiResponse<Category>>(`/admin/categories/${categoryId}/`, payload),
  deleteCategory: (categoryId: string) =>
    http.delete<ApiResponse<{ id: string; is_deleted: boolean }>>(
      `/admin/categories/${categoryId}/`,
    ),
  reorderCategories: (items: { id: string; parent_id: string | null; sort_order: number }[]) =>
    http.post<ApiResponse<Category[]>>('/admin/categories/reorder/', { items }),

  brands: () =>
    http.get<ApiResponse<Brand[]>>('/admin/brands/', {
      params: { page_size: 100 },
    }),
  createBrand: (payload: BrandPayload) => http.post<ApiResponse<Brand>>('/admin/brands/', payload),
  updateBrand: (brandId: string, payload: Partial<BrandPayload>) =>
    http.patch<ApiResponse<Brand>>(`/admin/brands/${brandId}/`, payload),
  deleteBrand: (brandId: string) =>
    http.delete<ApiResponse<{ id: string; is_deleted: boolean }>>(`/admin/brands/${brandId}/`),
}
