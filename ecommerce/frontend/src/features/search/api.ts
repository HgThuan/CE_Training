import type { PublicProductListItem } from '@/features/product/types'
import { http } from '@/shared/lib/http'
import type { ApiResponse } from '@/shared/types/api'

import type { SearchParams, SearchSuggestion, SmartSearchApiData, SmartSearchResult } from './types'

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

export function normalizeSmartSearchData(value: SmartSearchApiData | unknown): SmartSearchResult {
  const data = isRecord(value) ? value : {}
  const results = Array.isArray(data.results)
    ? (data.results as PublicProductListItem[])
    : Array.isArray(data.products)
      ? (data.products as PublicProductListItem[])
      : []
  const rawIntent = isRecord(data.intent) ? data.intent : {}
  const fallbackUsed = data.fallback_used === true

  return {
    results,
    explanation: typeof data.explanation === 'string' ? data.explanation.trim() : '',
    intent: {
      keywords: Array.isArray(rawIntent.keywords)
        ? rawIntent.keywords.filter((keyword): keyword is string => typeof keyword === 'string')
        : [],
      filters: isRecord(rawIntent.filters) ? rawIntent.filters : {},
    },
    ai_used: data.ai_used === true,
    fallback_used: fallbackUsed,
  }
}

export const searchApi = {
  search: (params: SearchParams) =>
    http.get<ApiResponse<PublicProductListItem[]>>('/search/', { params }),
  smartSearch: (params: SearchParams) =>
    http.get<ApiResponse<SmartSearchApiData>>('/ai/smart-search/', { params }),
  suggestions: (query: string, limit = 10) =>
    http.get<ApiResponse<SearchSuggestion[]>>('/search/suggestions/', {
      params: { q: query, limit },
    }),
}
