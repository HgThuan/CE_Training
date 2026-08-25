import { streamAssistantMessage } from './api'

describe('streamAssistantMessage', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('parses SSE events split across network chunks', async () => {
    const encoder = new TextEncoder()
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(encoder.encode('data: {"type":"stage","stage":"under'))
        controller.enqueue(
          encoder.encode('standing"}\r\n\r\ndata: {"type":"delta","text":"Xin chào"}\r\n\r\n'),
        )
        controller.close()
      },
    })
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(body, {
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)
    const events: unknown[] = []

    await streamAssistantMessage({ message: 'Xin chào' }, 'access-token', (event) =>
      events.push(event),
    )

    expect(events).toEqual([
      { type: 'stage', stage: 'understanding' },
      { type: 'delta', text: 'Xin chào' },
    ])
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/ai/assistant/messages',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({ Authorization: 'Bearer access-token' }),
      }),
    )
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ message: 'Xin chào' })
  })

  it('does not send an authorization header for guests', async () => {
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.close()
      },
    })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(body, { status: 200 })))

    await streamAssistantMessage(
      { message: 'Tìm quà sinh nhật', guest_token: 'guest-session-token-1234567890' },
      null,
      vi.fn(),
    )

    const headers = vi.mocked(fetch).mock.calls[0][1]?.headers as Record<string, string>
    expect(headers.Authorization).toBeUndefined()
  })

  it('refreshes an expired access token once and retries the SSE request', async () => {
    const encoder = new TextEncoder()
    const successBody = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(encoder.encode('data: {"type":"delta","text":"Đã kết nối lại"}\n\n'))
        controller.close()
      },
    })
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(null, { status: 401 }))
      .mockResolvedValueOnce(new Response(successBody, { status: 200 }))
    const refreshAccessToken = vi.fn().mockResolvedValue('fresh-access-token')
    vi.stubGlobal('fetch', fetchMock)
    const events: unknown[] = []

    await streamAssistantMessage(
      { message: 'Tìm tai nghe' },
      'expired-access-token',
      (event) => events.push(event),
      undefined,
      refreshAccessToken,
    )

    expect(refreshAccessToken).toHaveBeenCalledOnce()
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer expired-access-token')
    expect(fetchMock.mock.calls[1][1].headers.Authorization).toBe('Bearer fresh-access-token')
    expect(events).toEqual([{ type: 'delta', text: 'Đã kết nối lại' }])
  })

  it('refreshes an expired JWT before opening the SSE request', async () => {
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.close()
      },
    })
    const fetchMock = vi.fn().mockResolvedValue(new Response(body, { status: 200 }))
    const refreshAccessToken = vi.fn().mockResolvedValue('fresh-access-token')
    vi.stubGlobal('fetch', fetchMock)

    await streamAssistantMessage(
      { message: 'Tìm quà sinh nhật' },
      'header.eyJleHAiOjF9.signature',
      vi.fn(),
      undefined,
      refreshAccessToken,
    )

    expect(refreshAccessToken).toHaveBeenCalledOnce()
    expect(fetchMock).toHaveBeenCalledOnce()
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer fresh-access-token')
  })

  it('shows a useful message when the refresh session is no longer valid', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 401 })))

    await expect(
      streamAssistantMessage(
        { message: 'Xin chào' },
        'expired-access-token',
        vi.fn(),
        undefined,
        vi.fn().mockRejectedValue(new Error('Given token not valid for any token type')),
      ),
    ).rejects.toThrow('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại để tiếp tục.')
  })
})
