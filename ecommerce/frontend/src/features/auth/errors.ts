import axios from 'axios'

interface ApiErrorPayload {
  message?: string
  errors?: unknown
}

const fieldLabels: Record<string, string> = {
  email: 'Email',
  password: 'Mật khẩu',
  password_confirm: 'Xác nhận mật khẩu',
  full_name: 'Họ tên',
  phone: 'Số điện thoại',
  date_of_birth: 'Ngày sinh',
  gender: 'Giới tính',
  credentials: 'Thông tin đăng nhập',
  account: 'Tài khoản',
  non_field_errors: 'Dữ liệu',
}

function collectErrorMessages(value: unknown, field?: string): string[] {
  if (typeof value === 'string') {
    return [`${field ? `${fieldLabels[field] ?? field}: ` : ''}${value}`]
  }
  if (Array.isArray(value)) {
    return value.flatMap((item) => collectErrorMessages(item, field))
  }
  if (value && typeof value === 'object') {
    return Object.entries(value).flatMap(([key, item]) => collectErrorMessages(item, key))
  }
  return []
}

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError<ApiErrorPayload>(error)) {
    const payload = error.response?.data
    const details = collectErrorMessages(payload?.errors)
    if (details.length) return details.join(' · ')
    return payload?.message ?? 'Không thể kết nối tới máy chủ'
  }
  if (error instanceof Error && error.message) return error.message
  return 'Đã có lỗi không mong muốn xảy ra'
}
