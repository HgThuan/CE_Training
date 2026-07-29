export const BANNER_POSITIONS = ['hero', 'middle'] as const

export type BannerPosition = (typeof BANNER_POSITIONS)[number]

export interface Banner {
  id: string
  title: string | null
  image_url: string
  target_url: string | null
  position: BannerPosition
  sort_order: number
  starts_at: string | null
  ends_at: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface BannerPayload {
  title: string | null
  image_url: string
  target_url: string | null
  position: BannerPosition
  sort_order: number
  starts_at: string | null
  ends_at: string | null
  is_active: boolean
}
