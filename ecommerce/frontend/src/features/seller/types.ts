export type SellerApplicationStatus = 'pending' | 'approved' | 'rejected'
export type VerificationStatus = 'unverified' | 'pending' | 'verified'
export type DocumentReviewStatus = 'pending' | 'verified' | 'additional_required'
export type ShopStatus = 'pending' | 'approved' | 'rejected' | 'locked'

export interface SellerDocument {
  id: number
  document_type: 'id_card' | 'business_license' | 'tax_registration' | 'other'
  file_url: string
  original_name: string
  review_status: DocumentReviewStatus
  review_reason: string
  reviewed_at: string | null
  created_at: string
  updated_at: string
}

export interface SellerApplication {
  id: number
  business_name: string
  business_address: string
  tax_code: string
  contact_phone: string
  onboarding_status: SellerApplicationStatus
  rejection_reason: string
  verification_status: VerificationStatus
  submitted_at: string | null
  reviewed_at: string | null
  documents: SellerDocument[]
  created_at: string
  updated_at: string
}

export interface SellerApplicationPayload {
  business_name: string
  business_address: string
  tax_code: string
  contact_phone: string
}

export interface Shop {
  id: number
  owner_id: number
  owner_email: string
  name: string
  slug: string
  description: string
  logo_url: string
  cover_url: string
  status: ShopStatus
  lock_reason: string
  locked_at: string | null
  average_rating: string
  total_products: number
  created_at: string
  updated_at: string
}

export type ShopUpdatePayload = Partial<
  Pick<Shop, 'name' | 'description' | 'logo_url' | 'cover_url'>
>
