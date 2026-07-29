import type { Brand, Category, PublicProductListItem } from '@/features/product/types'
import type { PaginationMeta } from '@/shared/types/api'

export type SearchSort = '-created_at' | 'price' | '-price' | '-avg_rating' | '-sold_count'

export interface SearchParams {
  q: string
  category?: string
  brand?: string
  price_min?: string
  price_max?: string
  rating_min?: number
  in_stock?: boolean
  shop?: string
  sort?: SearchSort
  page?: number
  page_size?: number
}

export interface SearchSuggestion {
  id: string
  text: string
  slug?: string
  shop_slug?: string
}

export interface AiSearchIntent {
  keywords: string[]
  filters: Record<string, unknown>
}

export interface SmartSearchApiData {
  results?: PublicProductListItem[]
  products?: PublicProductListItem[]
  explanation?: string
  intent?: Partial<AiSearchIntent>
  ai_used?: boolean
  fallback_used?: boolean
}

export interface SmartSearchResult {
  results: PublicProductListItem[]
  explanation: string
  intent: AiSearchIntent
  ai_used: boolean
  fallback_used: boolean
}

export interface SearchFilterModel {
  category: string
  brand: string
  priceMin: string
  priceMax: string
  ratingMin: string
  inStock: boolean
  shop: string
}

export interface SearchPageState {
  products: PublicProductListItem[]
  meta: PaginationMeta
  categories: Category[]
  brands: Brand[]
}
