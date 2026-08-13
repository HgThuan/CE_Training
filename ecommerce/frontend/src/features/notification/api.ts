import { http } from '@/shared/lib/http'
import type { ApiResponse, PaginationMeta } from '@/shared/types/api'

import type { AppNotification } from './types'

interface NotificationMeta extends PaginationMeta {
  unread_count: number
}

export const notificationApi = {
  list: () =>
    http.get<ApiResponse<AppNotification[]> & { meta: NotificationMeta }>('/notifications', {
      params: { page_size: 100 },
    }),
  read: (id: number) => http.post<ApiResponse<AppNotification>>(`/notifications/${id}/read`, {}),
  readAll: () => http.post<ApiResponse<{ updated_count: number }>>('/notifications/read-all', {}),
}
