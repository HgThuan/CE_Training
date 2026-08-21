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
  const rawSlots = isRecord(rawIntent.slots) ? rawIntent.slots : {}
  const rawPriceRange = isRecord(rawSlots.price_range) ? rawSlots.price_range : {}

  return {
    results,
    explanation: typeof data.explanation === 'string' ? data.explanation.trim() : '',
    intent: {
      intent_type:
        typeof rawIntent.intent_type === 'string' ? rawIntent.intent_type : 'product_search',
      keywords: Array.isArray(rawIntent.keywords)
        ? rawIntent.keywords.filter((keyword): keyword is string => typeof keyword === 'string')
        : [],
      filters: isRecord(rawIntent.filters) ? rawIntent.filters : {},
      slots: {
        category_hints: Array.isArray(rawSlots.category_hints)
          ? rawSlots.category_hints.filter((item): item is string => typeof item === 'string')
          : [],
        price_range: {
          min:
            typeof rawPriceRange.min === 'string' || typeof rawPriceRange.min === 'number'
              ? rawPriceRange.min
              : null,
          max:
            typeof rawPriceRange.max === 'string' || typeof rawPriceRange.max === 'number'
              ? rawPriceRange.max
              : null,
        },
        attributes: isRecord(rawSlots.attributes)
          ? Object.fromEntries(
              Object.entries(rawSlots.attributes).map(([key, values]) => [
                key,
                Array.isArray(values)
                  ? values.filter((item): item is string => typeof item === 'string')
                  : [],
              ]),
            )
          : {},
        occasion: typeof rawSlots.occasion === 'string' ? rawSlots.occasion : null,
        recipient: typeof rawSlots.recipient === 'string' ? rawSlots.recipient : null,
      },
      confidence: typeof rawIntent.confidence === 'number' ? rawIntent.confidence : 0,
    },
    ai_used: data.ai_used === true,
    fallback_used: fallbackUsed,
    match_reasons: isRecord(data.match_reasons)
      ? Object.fromEntries(
          Object.entries(data.match_reasons).filter(
            (entry): entry is [string, string] => typeof entry[1] === 'string',
          ),
        )
      : {},
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
