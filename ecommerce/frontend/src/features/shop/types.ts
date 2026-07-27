import type { Shop } from '@/features/seller/types'

export interface PublicShopData {
  shop: Shop
  products: []
  available_filters: string[]
  available_sorts: string[]
}
