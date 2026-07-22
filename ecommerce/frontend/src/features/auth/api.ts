import { http } from '@/shared/lib/http'
import type { ApiResponse } from '@/shared/types/api'

import type {
  AuthenticatedUser,
  AuthTokenData,
  ChangePasswordPayload,
  LoginPayload,
  ProfilePayload,
  RegisterPayload,
  ResetPasswordPayload,
  UserRole,
} from './types'

export const authApi = {
  register: (payload: RegisterPayload) =>
    http.post<ApiResponse<AuthenticatedUser>>('/auth/register/', payload),
  verifyEmail: (token: string) =>
    http.post<ApiResponse<AuthenticatedUser>>('/auth/verify-email/', { token }),
  resendVerification: (email: string) =>
    http.post<ApiResponse<null>>('/auth/resend-verification/', { email }),
  login: (payload: LoginPayload) => http.post<ApiResponse<AuthTokenData>>('/auth/login/', payload),
  refresh: () => http.post<ApiResponse<AuthTokenData>>('/auth/refresh/', {}),
  logout: () => http.post<ApiResponse<null>>('/auth/logout/', {}),
  forgotPassword: (email: string) =>
    http.post<ApiResponse<null>>('/auth/forgot-password/', { email }),
  resetPassword: (payload: ResetPasswordPayload) =>
    http.post<ApiResponse<null>>('/auth/reset-password/', payload),
  me: () => http.get<ApiResponse<AuthenticatedUser>>('/users/me/'),
  updateProfile: (payload: ProfilePayload) =>
    http.patch<ApiResponse<AuthenticatedUser>>('/users/me/', payload),
  uploadAvatar: (avatar: Blob) => {
    const formData = new FormData()
    formData.append('avatar', avatar, 'avatar.jpg')
    return http.post<ApiResponse<AuthenticatedUser>>('/users/me/avatar/', formData)
  },
  changePassword: (payload: ChangePasswordPayload) =>
    http.post<ApiResponse<null>>('/users/me/change-password/', payload),
  assignRole: (userId: number, role: UserRole) =>
    http.post<ApiResponse<AuthenticatedUser>>(`/admin/users/${userId}/assign-role/`, { role }),
}
