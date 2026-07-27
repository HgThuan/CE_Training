import type { SellerApplication, Shop } from '@/features/seller/types'

export interface AdminSeller {
  id: number
  email: string
  full_name: string
  phone: string
  is_active: boolean
  role: 'seller'
  seller_profile: SellerApplication
  shop: Shop | null
  created_at: string
  updated_at: string
}

export interface SellerApplicationFilters {
  search?: string
  onboarding_status?: 'pending' | 'approved' | 'rejected'
  page?: number
  page_size?: number
}

export interface SellerFilters {
  search?: string
  is_active?: boolean
  shop__status?: 'approved' | 'locked'
  page?: number
  page_size?: number
}
