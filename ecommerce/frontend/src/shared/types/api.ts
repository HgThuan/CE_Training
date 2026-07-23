export interface PaginationMeta {
  page: number
  page_size: number
  total_items: number
  total_pages: number
}

export interface ApiResponse<T> {
  success: boolean
  message: string
  data: T
  errors?: Record<string, unknown>
  meta?: PaginationMeta
}
