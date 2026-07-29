import { http } from '@/shared/lib/http'
import type { ApiResponse } from '@/shared/types/api'

import type { Banner, BannerPayload } from './types'

export const adminBannersApi = {
  list: () =>
    http.get<ApiResponse<Banner[]>>('/admin/banners/', {
      params: { page_size: 100 },
    }),
  detail: (bannerId: string) => http.get<ApiResponse<Banner>>(`/admin/banners/${bannerId}/`),
  create: (payload: BannerPayload) => http.post<ApiResponse<Banner>>('/admin/banners/', payload),
  update: (bannerId: string, payload: Partial<BannerPayload>) =>
    http.patch<ApiResponse<Banner>>(`/admin/banners/${bannerId}/`, payload),
  delete: (bannerId: string) =>
    http.delete<ApiResponse<{ id: string; is_deleted: boolean }>>(`/admin/banners/${bannerId}/`),
  reorder: (sourceId: string, targetId: string) =>
    http.post<ApiResponse<Banner[]>>('/admin/banners/reorder/', {
      source_id: sourceId,
      target_id: targetId,
    }),
}
