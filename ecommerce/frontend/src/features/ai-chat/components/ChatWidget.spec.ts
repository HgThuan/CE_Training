import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'

import { useCompareStore } from '@/features/product/compare-store'

import { aiChatApi, streamChatTurn } from '../api'
import type { ChatMessage, ChatStreamEvent } from '../types'
import ChatWidget from './ChatWidget.vue'

vi.mock('../api', () => ({
  aiChatApi: {
    history: vi.fn(),
  },
  streamChatTurn: vi.fn(),
}))

describe('ChatWidget', () => {
  beforeEach(() => {
    window.localStorage.clear()
    vi.clearAllMocks()
  })

  it('streams assistant text and renders grounded product and comparison attachments', async () => {
    const finalMessage: ChatMessage = {
      id: 'assistant-1',
      session_id: 'session-1',
      role: 'assistant',
      content: 'Mình tìm thấy hai lựa chọn phù hợp.',
      attachments: [
        {
          type: 'product_card',
          product_id: 'product-1',
          product: { id: 'product-1', name: 'Laptop học tập' } as never,
        },
        {
          type: 'compare_table',
          product_ids: ['product-1', 'product-2'],
          comparison: { products: [] } as never,
        },
      ],
      created_at: '2026-08-14T00:00:00Z',
    }
    vi.mocked(streamChatTurn).mockImplementation(async (_payload, _token, onEvent) => {
      const events: ChatStreamEvent[] = [
        { type: 'session', session_id: 'session-1' },
        { type: 'delta', text: 'Mình tìm thấy ' },
        { type: 'delta', text: 'hai lựa chọn phù hợp.' },
        { type: 'done', message: finalMessage },
      ]
      for (const event of events) onEvent(event)
    })

    const wrapper = mount(ChatWidget, {
      global: {
        plugins: [createPinia()],
        stubs: {
          ChatProductCard: { template: '<article data-test="product-card" />' },
          ProductCompareTable: { template: '<section data-test="compare-table" />' },
        },
      },
    })
    await flushPromises()

    await wrapper.get('button[aria-label="Mở trợ lý mua sắm AI"]').trigger('click')
    await wrapper
      .findAll('button')
      .find((button) => button.text().includes('laptop'))!
      .trigger('click')
    await flushPromises()

    expect(streamChatTurn).toHaveBeenCalledWith(
      expect.objectContaining({
        message: 'Tìm laptop học tập dưới 20 triệu',
        guest_token: expect.any(String),
      }),
      null,
      expect.any(Function),
      expect.any(AbortSignal),
    )
    expect(wrapper.text()).toContain('Mình tìm thấy hai lựa chọn phù hợp.')
    expect(wrapper.findAll('[data-test="product-card"]')).toHaveLength(1)
    expect(wrapper.findAll('[data-test="compare-table"]')).toHaveLength(1)
    expect(window.localStorage.getItem('mercato.ai-chat.session:guest')).toBe('session-1')
  })

  it('starts a clean conversation without showing an abort as an error', async () => {
    vi.mocked(streamChatTurn).mockImplementation(
      (_payload, _token, _onEvent, signal) =>
        new Promise<void>((_resolve, reject) => {
          signal?.addEventListener('abort', () => {
            reject(new DOMException('Aborted', 'AbortError'))
          })
        }),
    )
    const wrapper = mount(ChatWidget, {
      global: { plugins: [createPinia()] },
    })
    await flushPromises()
    await wrapper.get('button[aria-label="Mở trợ lý mua sắm AI"]').trigger('click')
    await wrapper
      .findAll('button')
      .find((button) => button.text().includes('laptop'))!
      .trigger('click')

    await wrapper.get('button[aria-label="Bắt đầu cuộc trò chuyện mới"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Hôm nay bạn muốn tìm gì?')
    expect(wrapper.text()).not.toContain('Aborted')
  })

  it('moves focus into the panel and returns it to the launcher on Escape', async () => {
    const wrapper = mount(ChatWidget, {
      attachTo: document.body,
      global: { plugins: [createPinia()] },
    })
    await flushPromises()

    await wrapper.get('button[aria-label="Mở trợ lý mua sắm AI"]').trigger('click')
    await flushPromises()
    expect(document.activeElement?.id).toBe('ai-shopping-assistant')

    await wrapper.get('#ai-shopping-assistant').trigger('keydown', { key: 'Escape' })
    await flushPromises()
    expect(document.activeElement?.getAttribute('aria-label')).toBe('Mở trợ lý mua sắm AI')
    wrapper.unmount()
  })

  it('keeps the session pointer when history temporarily fails and allows retry', async () => {
    window.localStorage.setItem('mercato.ai-chat.session:guest', 'session-to-retry')
    vi.mocked(aiChatApi.history).mockRejectedValueOnce(new Error('Network unavailable'))
    const wrapper = mount(ChatWidget, {
      global: { plugins: [createPinia()] },
    })
    await flushPromises()
    await wrapper.get('button[aria-label="Mở trợ lý mua sắm AI"]').trigger('click')

    expect(window.localStorage.getItem('mercato.ai-chat.session:guest')).toBe('session-to-retry')
    expect(wrapper.text()).toContain('Phiên vẫn được giữ')

    vi.mocked(aiChatApi.history).mockResolvedValueOnce({
      data: {
        data: [
          {
            id: 'history-1',
            role: 'assistant',
            content: 'Cuộc trò chuyện đã được khôi phục.',
            attachments: [],
            created_at: '2026-08-14T00:00:00Z',
          },
        ],
      },
    } as never)
    await wrapper
      .findAll('button')
      .find((button) => button.text().includes('Thử lại'))!
      .trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Cuộc trò chuyện đã được khôi phục.')
    expect(wrapper.text()).not.toContain('Phiên vẫn được giữ')
  })

  it('yields the bottom action area to the product comparison workflow', async () => {
    const pinia = createPinia()
    const compareBar = document.createElement('aside')
    compareBar.id = 'product-compare-bar'
    compareBar.tabIndex = -1
    document.body.append(compareBar)
    const wrapper = mount(ChatWidget, {
      attachTo: document.body,
      global: { plugins: [pinia] },
    })
    await flushPromises()
    await wrapper.get('button[aria-label="Mở trợ lý mua sắm AI"]').trigger('click')

    useCompareStore(pinia).toggle({ id: 'product-1', name: 'Laptop A' } as never)
    await flushPromises()

    expect(wrapper.find('button[aria-label="Mở trợ lý mua sắm AI"]').exists()).toBe(false)
    expect(document.activeElement).toBe(compareBar)
    wrapper.unmount()
    compareBar.remove()
  })
})
