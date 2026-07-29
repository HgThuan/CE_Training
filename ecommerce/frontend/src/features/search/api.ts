import type { PublicProductListItem } from '@/features/product/types'
import { http } from '@/shared/lib/http'
import type { ApiResponse } from '@/shared/types/api'

import type { SearchParams, SearchSuggestion } from './types'

export const searchApi = {
  search: (params: SearchParams) =>
    http.get<ApiResponse<PublicProductListItem[]>>('/search/', { params }),
  suggestions: (query: string, limit = 10) =>
    http.get<ApiResponse<SearchSuggestion[]>>('/search/suggestions/', {
      params: { q: query, limit },
    }),
}
