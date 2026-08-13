import { mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { notificationApi } from '../api'
import { useNotifications } from './useNotifications'

vi.mock('../api', () => ({
  notificationApi: {
    list: vi.fn(),
    read: vi.fn(),
    readAll: vi.fn(),
  },
}))

class FakeWebSocket {
  static readonly OPEN = 1
  static instances: FakeWebSocket[] = []

  readyState = FakeWebSocket.OPEN
  onopen: (() => void) | null = null
  onmessage: ((event: MessageEvent<string>) => void) | null = null
  onclose: (() => void) | null = null
  onerror: (() => void) | null = null

  constructor(public readonly url: string) {
    FakeWebSocket.instances.push(this)
  }

  close(): void {}
}

const emptyResponse = {
  data: {
    success: true,
    message: 'ok',
    data: [],
    meta: { page: 1, page_size: 100, total_items: 0, total_pages: 0, unread_count: 0 },
  },
}

describe('useNotifications', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    FakeWebSocket.instances = []
    vi.stubGlobal('WebSocket', FakeWebSocket)
    vi.mocked(notificationApi.list).mockResolvedValue(emptyResponse as never)
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  it('falls back to polling and reconnects after the socket closes', async () => {
    let center!: ReturnType<typeof useNotifications>
    const wrapper = mount(
      defineComponent({
        setup() {
          center = useNotifications(() => 'access-token')
          return () => h('div')
        },
      }),
    )

    await center.start()
    expect(FakeWebSocket.instances[0]?.url).toContain('/ws/notifications?token=access-token')

    FakeWebSocket.instances[0]?.onclose?.()
    await vi.advanceTimersByTimeAsync(30_000)

    expect(notificationApi.list).toHaveBeenCalledTimes(2)
    expect(FakeWebSocket.instances.length).toBeGreaterThan(1)
    wrapper.unmount()
  })
})
