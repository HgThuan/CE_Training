import axios from 'axios'

interface ApiErrorPayload {
  message?: string
}

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError<ApiErrorPayload>(error)) {
    return error.response?.data?.message ?? 'Không thể kết nối tới máy chủ'
  }
  return 'Đã có lỗi không mong muốn xảy ra'
}
