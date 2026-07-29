import type { PublicProductListItem } from '@/features/product/types'

export interface WishlistItem {
  id: string
  product: PublicProductListItem
  price_when_added: string | null
  created_at: string
}

export interface WishlistToggleResult {
  product_id: string
  is_wishlisted: boolean
  item: WishlistItem | null
}

export interface WishlistListParams {
  page?: number
  page_size?: number
}
