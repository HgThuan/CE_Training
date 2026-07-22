import { http } from '@/shared/lib/http'
import type { ApiResponse } from '@/shared/types/api'

import type {
  AdminCustomer,
  CustomerCreatePayload,
  CustomerListFilters,
  CustomerUpdatePayload,
} from './types'

export const adminUsersApi = {
  listCustomers: (filters: CustomerListFilters) =>
    http.get<ApiResponse<AdminCustomer[]>>('/admin/customers/', { params: filters }),
  getCustomer: (customerId: number) =>
    http.get<ApiResponse<AdminCustomer>>(`/admin/customers/${customerId}/`),
  createCustomer: (payload: CustomerCreatePayload) =>
    http.post<ApiResponse<AdminCustomer>>('/admin/customers/', payload),
  updateCustomer: (customerId: number, payload: CustomerUpdatePayload) =>
    http.patch<ApiResponse<AdminCustomer>>(`/admin/customers/${customerId}/`, payload),
  deleteCustomer: (customerId: number) =>
    http.delete<ApiResponse<null>>(`/admin/customers/${customerId}/`),
  lockUser: (userId: number, reason: string) =>
    http.post<ApiResponse<AdminCustomer>>(`/admin/users/${userId}/lock/`, { reason }),
  unlockUser: (userId: number, reason: string) =>
    http.post<ApiResponse<AdminCustomer>>(`/admin/users/${userId}/unlock/`, { reason }),
  resetPassword: (userId: number, reason: string) =>
    http.post<ApiResponse<null>>(`/admin/users/${userId}/reset-password/`, { reason }),
}
