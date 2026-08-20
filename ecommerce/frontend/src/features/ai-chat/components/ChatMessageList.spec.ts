import { mount } from '@vue/test-utils'

import type { ChatMessage } from '../types'
import ChatMessageList from './ChatMessageList.vue'

describe('ChatMessageList', () => {
  it('renders assistant Markdown as readable, semantic content', () => {
    const message: ChatMessage = {
      id: 'assistant-rich-text',
      role: 'assistant',
      content: `Hiện tại Mercato chưa có dòng đồng hồ chuyên dụng.

Tuy nhiên, bạn có thể tham khảo:

- **Đồng hồ Samsung Galaxy Watch6**
  - **Giá:** 5.490.000 đ – 5.990.000 đ
  - **Đánh giá:** 4.68 ⭐ (71 đánh giá)

*Lưu ý: Vui lòng kiểm tra giá trên card sản phẩm trước khi mua.*`,
      attachments: [],
      created_at: '2026-08-14T00:00:00Z',
    }

    const wrapper = mount(ChatMessageList, {
      props: { messages: [message], isStreaming: false },
    })

    expect(wrapper.text()).not.toContain('**')
    expect(wrapper.get('strong').text()).toBe('Đồng hồ Samsung Galaxy Watch6')
    expect(wrapper.findAll('.chat-rich-text li')).toHaveLength(3)
    expect(wrapper.get('[role="note"]').text()).toContain('Vui lòng kiểm tra giá')
  })

  it('offers relevant follow-up actions after the latest assistant response', async () => {
    const message: ChatMessage = {
      id: 'assistant-follow-up',
      role: 'assistant',
      content: 'Mình đã tìm được một lựa chọn phù hợp.',
      attachments: [
        {
          type: 'product_card',
          product_id: 'product-1',
          product: { id: 'product-1', name: 'Đồng hồ thông minh' } as never,
        },
      ],
      created_at: '2026-08-14T00:00:00Z',
    }
    const wrapper = mount(ChatMessageList, {
      props: { messages: [message], isStreaming: false },
      global: {
        stubs: { ChatProductCard: { template: '<article />' } },
      },
    })

    expect(wrapper.text()).toContain('Gợi ý gần nhu cầu')
    expect(wrapper.text()).toContain('chỉ khớp một phần')

    await wrapper
      .findAll('button')
      .find((button) => button.text().includes('Tìm sản phẩm tương tự'))!
      .trigger('click')

    expect(wrapper.emitted('followUp')).toEqual([['Tìm sản phẩm tương tự']])
  })

  it('separates verified matches from alternative products', () => {
    const baseProduct = { id: 'product', name: 'Laptop' } as never
    const message: ChatMessage = {
      id: 'assistant-groups',
      role: 'assistant',
      content: 'Mình đã kiểm tra các tiêu chí từ dữ liệu Mercato.',
      attachments: [
        {
          type: 'product_card',
          product_id: 'exact-product',
          product: baseProduct,
          match: { kind: 'exact', matched_terms: ['laptop'], missing_terms: [] },
        },
        {
          type: 'product_card',
          product_id: 'alternative-product',
          product: baseProduct,
          match: {
            kind: 'alternative',
            matched_terms: ['laptop'],
            missing_terms: ['budget_max:20000000'],
          },
        },
      ],
      created_at: '2026-08-14T00:00:00Z',
    }

    const wrapper = mount(ChatMessageList, {
      props: { messages: [message], isStreaming: false },
      global: { stubs: { ChatProductCard: { template: '<article />' } } },
    })

    expect(wrapper.text()).toContain('Khớp với nhu cầu')
    expect(wrapper.text()).toContain('Gợi ý gần nhu cầu')
    expect(wrapper.text()).toContain('vượt ngân sách tối đa 20.000.000')
  })
})
