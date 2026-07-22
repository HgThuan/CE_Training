export interface Address {
  id: number
  recipient_name: string
  phone: string
  province: string
  district: string
  ward: string
  detail_address: string
  is_default: boolean
  created_at: string
  updated_at: string
}

export type AddressPayload = Omit<Address, 'id' | 'created_at' | 'updated_at'>
