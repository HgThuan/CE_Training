import { streamChatTurn } from './api'

describe('streamChatTurn', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('parses SSE events split across network chunks', async () => {
    const encoder = new TextEncoder()
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(encoder.encode('data: {"type":"delta","te'))
        controller.enqueue(encoder.encode('xt":"Xin chào"}\r\n\r\ndata: {"type":"done",'))
        controller.enqueue(
          encoder.encode(
            '"message":{"id":"m1","role":"assistant","content":"Xin chào","attachments":[],"created_at":"now"}}',
          ),
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

    await streamChatTurn(
      { guest_token: 'guest-token', message: 'Xin chào' },
      'access-token',
      (event) => events.push(event),
    )

    expect(events).toEqual([
      { type: 'delta', text: 'Xin chào' },
      {
        type: 'done',
        message: {
          id: 'm1',
          role: 'assistant',
          content: 'Xin chào',
          attachments: [],
          created_at: 'now',
        },
      },
    ])
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/chat/turn',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({ Authorization: 'Bearer access-token' }),
      }),
    )
  })
})
