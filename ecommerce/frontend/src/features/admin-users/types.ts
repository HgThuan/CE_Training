import type { CustomerProfile } from '@/features/auth/types'

export interface AdminCustomer {
  id: number
  email: string
  full_name: string
  phone: string
  is_active: boolean
  is_email_verified: boolean
  must_change_password: boolean
  created_at: string
  avatar_url?: string
  date_of_birth?: string | null
  gender?: '' | 'male' | 'female' | 'other'
  is_deleted?: boolean
  deleted_at?: string | null
  lock_reason?: string
  locked_at?: string | null
  profile?: CustomerProfile
  updated_at?: string
}

export interface CustomerCreatePayload {
  email: string
  password: string
  password_confirm: string
  full_name: string
  phone: string
  date_of_birth: string | null
  gender: '' | 'male' | 'female' | 'other'
  is_email_verified: boolean
}

export type CustomerUpdatePayload = Partial<
  Pick<
    CustomerCreatePayload,
    'email' | 'full_name' | 'phone' | 'date_of_birth' | 'gender' | 'is_email_verified'
  >
>

export interface CustomerListFilters {
  search?: string
  is_active?: boolean
  page?: number
  page_size?: number
}
