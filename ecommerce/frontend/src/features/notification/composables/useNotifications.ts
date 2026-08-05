import { onBeforeUnmount, ref } from 'vue'

import { websocketUrl } from '@/shared/lib/websocket'

import { notificationApi } from '../api'
import type { AppNotification } from '../types'

interface NotificationEvent {
  type: 'notification'
  data: AppNotification
}

export function useNotifications(accessToken: () => string | null) {
  const notifications = ref<AppNotification[]>([])
  const unreadCount = ref(0)
  const connected = ref(false)
  let socket: WebSocket | null = null
  let pollTimer: number | null = null
  let reconnectTimer: number | null = null
  let reconnectAttempts = 0
  let disposed = false

  async function refresh(): Promise<void> {
    const response = await notificationApi.list()
    notifications.value = response.data.data
    unreadCount.value = response.data.meta.unread_count
  }

  function startPolling(): void {
    if (pollTimer !== null) return
    pollTimer = window.setInterval(() => void refresh(), 30_000)
  }

  function stopPolling(): void {
    if (pollTimer !== null) window.clearInterval(pollTimer)
    pollTimer = null
  }

  function connect(): void {
    const token = accessToken()
    if (!token || disposed) return
    socket?.close()
    socket = new WebSocket(websocketUrl('/ws/notifications', token))
    socket.onopen = () => {
      connected.value = true
      reconnectAttempts = 0
      stopPolling()
    }
    socket.onmessage = (event) => {
      const payload = JSON.parse(String(event.data)) as NotificationEvent
      if (payload.type !== 'notification') return
      notifications.value = [
        payload.data,
        ...notifications.value.filter((item) => item.id !== payload.data.id),
      ]
      if (!payload.data.is_read) unreadCount.value += 1
    }
    socket.onclose = () => {
      connected.value = false
      startPolling()
      if (disposed || reconnectTimer !== null) return
      const delay = Math.min(1_000 * 2 ** reconnectAttempts, 15_000)
      reconnectAttempts += 1
      reconnectTimer = window.setTimeout(() => {
        reconnectTimer = null
        connect()
      }, delay)
    }
    socket.onerror = () => socket?.close()
  }

  async function start(): Promise<void> {
    await refresh()
    connect()
  }

  async function markRead(notification: AppNotification): Promise<void> {
    if (notification.is_read) return
    const response = await notificationApi.read(notification.id)
    Object.assign(notification, response.data.data)
    unreadCount.value = Math.max(0, unreadCount.value - 1)
  }

  async function markAllRead(): Promise<void> {
    await notificationApi.readAll()
    notifications.value.forEach((notification) => {
      notification.is_read = true
      notification.read_at = new Date().toISOString()
    })
    unreadCount.value = 0
  }

  onBeforeUnmount(() => {
    disposed = true
    stopPolling()
    if (reconnectTimer !== null) window.clearTimeout(reconnectTimer)
    socket?.close()
  })

  return { notifications, unreadCount, connected, start, refresh, markRead, markAllRead }
}
