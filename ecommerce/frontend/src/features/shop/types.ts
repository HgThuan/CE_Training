import type { PublicProductListItem } from '@/features/product/types'

export interface PublicShop {
  id: number
  name: string
  slug: string
  description: string
  logo_url: string
  cover_url: string
  average_rating: string
  total_products: number
  follower_count: number
  is_following: boolean
  created_at: string
}

export interface PublicShopData {
  shop: PublicShop
  products: PublicProductListItem[]
  available_filters: string[]
  available_sorts: string[]
}

export interface ShopFollowResult {
  shop_id: number
  is_following: boolean
  follower_count: number
}

export type PublicShopSort = 'newest' | 'price_asc' | 'price_desc' | 'rating'
