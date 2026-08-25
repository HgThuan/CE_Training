import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'

import { useCompareStore } from '@/features/product/compare-store'
import { useAuthStore } from '@/stores/auth'

import { aiChatApi, streamAssistantMessage } from '../api'
import type { ChatMessage, ChatStreamEvent } from '../types'
import ChatWidget from './ChatWidget.vue'

vi.mock('../api', () => ({
  aiChatApi: {
    conversations: vi.fn(),
    conversation: vi.fn(),
    deleteConversation: vi.fn(),
    feedback: vi.fn(),
  },
  streamAssistantMessage: vi.fn(),
}))

const customer = {
  id: 10,
  email: 'customer@example.com',
  role: 'customer',
  full_name: 'Customer',
}

function authenticatedPinia() {
  const pinia = createPinia()
  const authStore = useAuthStore(pinia)
  authStore.accessToken = 'access-token'
  authStore.user = customer as never
  return pinia
}

describe('ChatWidget', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(aiChatApi.conversations).mockResolvedValue({
      data: { data: [] },
    } as never)
  })

  it('streams stages and renders grounded product attachments for a customer', async () => {
    const finalMessage: ChatMessage = {
      id: 'assistant-1',
      conversation_id: 'conversation-1',
      role: 'assistant',
      content: 'Mình tìm thấy lựa chọn phù hợp.',
      attachments: [
        {
          type: 'product_card',
          product_id: 'product-1',
          product: { id: 'product-1', name: 'Laptop học tập' } as never,
          match: { kind: 'exact', matched_terms: ['đúng ngân sách'], missing_terms: [] },
          reason: 'đúng ngân sách',
        },
      ],
      created_at: '2026-08-14T00:00:00Z',
    }
    vi.mocked(streamAssistantMessage).mockImplementation(async (_payload, _token, onEvent) => {
      const events: ChatStreamEvent[] = [
        { type: 'conversation', conversation_id: 'conversation-1' },
        { type: 'stage', stage: 'retrieving' },
        { type: 'delta', text: 'Mình tìm thấy lựa chọn phù hợp.' },
        { type: 'done', message: finalMessage },
      ]
      events.forEach(onEvent)
    })

    const wrapper = mount(ChatWidget, {
      global: {
        plugins: [authenticatedPinia()],
        stubs: { ChatProductCard: { template: '<article data-test="product-card" />' } },
      },
    })
    await flushPromises()
    await wrapper.get('button[aria-label="Mở trợ lý mua sắm AI"]').trigger('click')
    await wrapper
      .findAll('button')
      .find((button) => button.text().includes('laptop'))!
      .trigger('click')
    await flushPromises()

    expect(streamAssistantMessage).toHaveBeenCalledWith(
      expect.objectContaining({ message: 'Tìm laptop học tập dưới 20 triệu' }),
      'access-token',
      expect.any(Function),
      expect.any(AbortSignal),
    )
    expect(wrapper.text()).toContain('Mình tìm thấy lựa chọn phù hợp.')
    expect(wrapper.findAll('[data-test="product-card"]')).toHaveLength(1)
  })

  it('lets guests start shopping assistance without a login wall', async () => {
    const wrapper = mount(ChatWidget, { global: { plugins: [createPinia()] } })
    await flushPromises()
    await wrapper.get('button[aria-label="Mở trợ lý mua sắm AI"]').trigger('click')

    expect(wrapper.text()).not.toContain('Đăng nhập để tiếp tục')
    expect(wrapper.find('textarea').exists()).toBe(true)
  })

  it('moves focus into the panel and returns it to the launcher on Escape', async () => {
    const wrapper = mount(ChatWidget, {
      attachTo: document.body,
      global: { plugins: [authenticatedPinia()] },
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

  it('yields the bottom action area to product comparison', async () => {
    const pinia = authenticatedPinia()
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
