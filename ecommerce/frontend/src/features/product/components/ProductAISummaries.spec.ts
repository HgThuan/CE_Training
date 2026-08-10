import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, vi } from 'vitest'

import { productApi } from '../api'
import ProductAIReviewSummary from './ProductAIReviewSummary.vue'
import ProductAISummary from './ProductAISummary.vue'

vi.mock('../api', () => ({
  productApi: {
    aiSummary: vi.fn(),
    aiReviewSummary: vi.fn(),
  },
}))

function response<T>(data: T) {
  return { data: { success: true, message: 'ok', data } } as never
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((promiseResolve) => {
    resolve = promiseResolve
  })
  return { promise, resolve }
}

describe('product AI summaries', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows a skeleton then labels an AI-generated product summary', async () => {
    const request = deferred<Awaited<ReturnType<typeof productApi.aiSummary>>>()
    vi.mocked(productApi.aiSummary).mockReturnValue(request.promise)
    const wrapper = mount(ProductAISummary, { props: { productId: 'product-1' } })

    expect(wrapper.get('[role="status"]').attributes('aria-label')).toContain('sản phẩm')

    request.resolve(
      response({
        summary: 'Tóm tắt sản phẩm.',
        highlights: ['Pin tốt'],
        target_audience: 'Người hay di chuyển',
        key_specs: { Pin: 'Cả ngày' },
        is_ai_generated: true,
        ai_label: 'Tạo bởi AI',
      }),
    )
    await flushPromises()

    expect(wrapper.text()).toContain('Tóm tắt sản phẩm.')
    expect(wrapper.text()).toContain('Tạo bởi AI')
  })

  it('never shows the AI badge for a rule-based product fallback', async () => {
    vi.mocked(productApi.aiSummary).mockResolvedValue(
      response({
        summary: 'Hai câu đầu từ mô tả.',
        highlights: [],
        target_audience: '',
        key_specs: {},
        is_ai_generated: false,
        ai_label: null,
      }),
    )

    const wrapper = mount(ProductAISummary, { props: { productId: 'product-1' } })
    await flushPromises()

    expect(wrapper.text()).toContain('Hai câu đầu từ mô tả.')
    expect(wrapper.text()).not.toContain('Tạo bởi AI')
  })

  it('hides the product summary after an API error', async () => {
    vi.mocked(productApi.aiSummary).mockRejectedValue(new Error('network'))

    const wrapper = mount(ProductAISummary, { props: { productId: 'product-1' } })
    await flushPromises()

    expect(wrapper.text()).toBe('')
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  })

  it('renders structured review insights and the AI badge only for AI output', async () => {
    vi.mocked(productApi.aiReviewSummary).mockResolvedValue(
      response({
        summary: 'Khách hàng nhìn chung hài lòng.',
        pros: ['Dễ dùng'],
        cons: ['Bao bì đơn giản'],
        sentiment: 'positive' as const,
        sample_count: 12,
        is_ai_generated: true,
        ai_label: 'Tạo bởi AI',
      }),
    )

    const wrapper = mount(ProductAIReviewSummary, { props: { productId: 'product-1' } })
    await flushPromises()

    expect(wrapper.text()).toContain('Khách hàng nhìn chung hài lòng.')
    expect(wrapper.text()).toContain('Dễ dùng')
    expect(wrapper.text()).toContain('Bao bì đơn giản')
    expect(wrapper.text()).toContain('Tạo bởi AI')
  })

  it('hides a failed review summary request', async () => {
    vi.mocked(productApi.aiReviewSummary).mockRejectedValue(new Error('rate limited'))

    const wrapper = mount(ProductAIReviewSummary, { props: { productId: 'product-1' } })
    await flushPromises()

    expect(wrapper.text()).toBe('')
    expect(wrapper.find('[role="alert"]').exists()).toBe(false)
  })
})
