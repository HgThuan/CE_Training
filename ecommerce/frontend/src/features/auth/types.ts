export type UserRole = 'admin' | 'seller' | 'customer'

export interface CustomerProfile {
  loyalty_points: number
  wallet_balance: string
}

export interface SellerProfile {
  onboarding_status: 'pending' | 'approved' | 'rejected'
  rejection_reason: string
  id_card_document_url: string
  business_license_url: string
  verification_status: 'unverified' | 'pending' | 'verified'
}

export interface AdminProfile {
  permission_level: string
}

export interface AuthenticatedUser {
  id: number
  email: string
  role: UserRole
  is_active: boolean
  is_email_verified: boolean
  must_change_password: boolean
  avatar_url: string
  full_name: string
  phone: string
  date_of_birth: string | null
  gender: '' | 'male' | 'female' | 'other'
  profile: CustomerProfile | SellerProfile | AdminProfile | null
  created_at: string
  updated_at: string
}

export interface AuthTokenData {
  access: string
  access_expires_in: number
  user: AuthenticatedUser
}

export interface RegisterPayload {
  email: string
  password: string
  password_confirm: string
  full_name: string
}

export interface LoginPayload {
  email: string
  password: string
}

export interface ProfilePayload {
  full_name?: string
  phone?: string
  date_of_birth?: string | null
  gender?: '' | 'male' | 'female' | 'other'
}

export interface ResetPasswordPayload {
  uid: string
  token: string
  new_password: string
  new_password_confirm: string
}

export interface ChangePasswordPayload {
  old_password: string
  new_password: string
  new_password_confirm: string
}
