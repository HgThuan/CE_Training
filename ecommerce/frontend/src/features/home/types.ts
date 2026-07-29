import type { PublicProductListItem } from '@/features/product/types'

export interface HomeBanner {
  id: string
  title: string | null
  image_url: string
  target_url: string | null
  position: 'hero' | 'middle'
  sort_order: number
}

export interface HomeCategory {
  id: string
  name: string
  slug: string
  image_url: string | null
}

export interface HomePageData {
  banners: HomeBanner[]
  new_arrivals: PublicProductListItem[]
  best_sellers: PublicProductListItem[]
  categories: HomeCategory[]
}
