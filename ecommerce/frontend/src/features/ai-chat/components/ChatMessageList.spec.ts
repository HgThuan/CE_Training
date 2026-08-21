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

  it('renders grounded order actions and emits message feedback', async () => {
    const message: ChatMessage = {
      id: 'assistant-order',
      role: 'assistant',
      content: 'Đây là trạng thái OMS mới nhất.',
      attachments: [
        {
          type: 'order_card',
          order: {
            id: 'order-1',
            order_code: 'ORD-20260820-ABCDEF1234',
            placed_at: '2026-08-20T08:00:00Z',
            grand_total: '230000',
            currency: 'VND',
            payment_status: 'PAID',
            payment_status_label: 'Đã thanh toán',
            payment_method: 'COD',
            payment_method_label: 'Thanh toán khi nhận hàng',
            shop_orders: [
              {
                id: 'shop-order-1',
                shop_order_code: 'SORD-20260820-ABCDEF1234',
                shop_name: 'Mercato Shop',
                fulfillment_status: 'SHIPPING',
                fulfillment_status_label: 'Đang giao',
                shipping_method: 'Giao hàng tiêu chuẩn',
                estimated_delivery_at: null,
                last_status_at: '2026-08-20T09:00:00Z',
                return_eligible: false,
                return_deadline: null,
                items: [{ id: 'item-1', name: 'Tai nghe', variant: '', quantity: 1 }],
                return_requests: [],
              },
            ],
          },
        },
        {
          type: 'quick_actions',
          actions: [
            { label: 'Kiểm tra đổi/trả', kind: 'reply', value: 'Kiểm tra đổi trả đơn này' },
          ],
        },
      ],
      created_at: '2026-08-20T09:00:00Z',
    }
    const wrapper = mount(ChatMessageList, {
      props: { messages: [message], isStreaming: false },
    })

    expect(wrapper.text()).toContain('ORD-20260820-ABCDEF1234')
    expect(wrapper.text()).toContain('Mercato Shop')
    expect(wrapper.text()).toContain('Đang giao')

    await wrapper.get('button[aria-label="Câu trả lời hữu ích"]').trigger('click')
    await wrapper
      .findAll('button')
      .find((button) => button.text().includes('Kiểm tra đổi/trả'))!
      .trigger('click')

    expect(wrapper.emitted('feedback')).toEqual([['assistant-order', 5]])
    expect(wrapper.emitted('followUp')).toEqual([['Kiểm tra đổi trả đơn này']])
  })
})
