import { http } from '@/shared/lib/http'
import type { ApiResponse } from '@/shared/types/api'

import type { Address, AddressPayload } from './types'

export const accountApi = {
  listAddresses: () => http.get<ApiResponse<Address[]>>('/users/me/addresses/'),
  createAddress: (payload: AddressPayload) =>
    http.post<ApiResponse<Address>>('/users/me/addresses/', payload),
  updateAddress: (addressId: number, payload: Partial<AddressPayload>) =>
    http.patch<ApiResponse<Address>>(`/users/me/addresses/${addressId}/`, payload),
  deleteAddress: (addressId: number) =>
    http.delete<ApiResponse<null>>(`/users/me/addresses/${addressId}/`),
  setDefaultAddress: (addressId: number) =>
    http.post<ApiResponse<Address>>(`/users/me/addresses/${addressId}/set-default/`, {}),
}
