export interface AppNotification {
  id: number
  notification_type: string
  title: string
  message: string
  data: Record<string, unknown>
  is_read: boolean
  read_at: string | null
  created_at: string
}
