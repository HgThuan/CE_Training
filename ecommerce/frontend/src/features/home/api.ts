import { http } from '@/shared/lib/http'
import type { ApiResponse } from '@/shared/types/api'

import type { HomePageData } from './types'

export const homeApi = {
  get: () => http.get<ApiResponse<HomePageData>>('/home/'),
}
