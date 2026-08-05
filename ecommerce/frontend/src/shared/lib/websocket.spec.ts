import { afterEach, describe, expect, it, vi } from 'vitest'

import { websocketUrl } from './websocket'

describe('websocketUrl', () => {
  afterEach(() => vi.unstubAllEnvs())

  it('does not duplicate the ws prefix when it is included in the configured base', () => {
    vi.stubEnv('VITE_WS_BASE_URL', 'ws://localhost:8080/ws')

    expect(websocketUrl('/ws/chat/conversation-id', 'access token')).toBe(
      'ws://localhost:8080/ws/chat/conversation-id?token=access%20token',
    )
  })

  it('keeps the ws route when the configured base is only an origin', () => {
    vi.stubEnv('VITE_WS_BASE_URL', 'ws://localhost:8080')

    expect(websocketUrl('/ws/notifications', 'token')).toBe(
      'ws://localhost:8080/ws/notifications?token=token',
    )
  })
})
