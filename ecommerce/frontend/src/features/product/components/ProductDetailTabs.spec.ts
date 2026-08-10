import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'

import type { PublicProductDetail } from '../types'
import ProductDetailTabs from './ProductDetailTabs.vue'

vi.mock('@/features/after-sales/api', () => ({
  afterSalesApi: {
    productReviews: vi.fn().mockResolvedValue({ data: { data: [] } }),
  },
}))

const product: PublicProductDetail = {
  id: 'product-1',
  name: 'Điện thoại mới',
  slug: 'dien-thoai-moi',
  short_description: 'Mẫu điện thoại mới',
  description: 'Mô tả chi tiết sản phẩm.',
  category: { id: 'category-1', name: 'Điện thoại', slug: 'dien-thoai' },
  brand: null,
  shop: {
    id: 1,
    name: 'Future Shop',
    slug: 'future-shop',
    logo_url: null,
    average_rating: '4.8',
  },
  media: [],
  variants: [],
  attributes: [],
  min_price: '1000000',
  max_price: '1000000',
  rating_average: '4.8',
  rating_count: 10,
  sold_count: 20,
  created_at: '2026-07-01T00:00:00Z',
  updated_at: '2026-07-01T00:00:00Z',
}

async function mountTabs(initialPath = '/products/dien-thoai-moi') {
  const routeComponent = { template: '<div />' }
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/products/:slug', component: routeComponent }],
  })
  await router.push(initialPath)
  await router.isReady()
  await flushPromises()

  const wrapper = mount(ProductDetailTabs, {
    props: { product },
    global: {
      plugins: [router],
      stubs: {
        QASection: { template: '<div data-test="qa-section">Nội dung hỏi đáp</div>' },
        ProductAISummary: true,
        ProductAIReviewSummary: true,
      },
    },
  })
  return { router, wrapper }
}

describe('ProductDetailTabs', () => {
  it('opens the tab selected by the URL hash', async () => {
    const { wrapper } = await mountTabs('/products/dien-thoai-moi#qa')

    expect(wrapper.get('[data-test="qa-section"]').text()).toBe('Nội dung hỏi đáp')
    expect(wrapper.get('#product-tab-qa').attributes('aria-selected')).toBe('true')
    wrapper.unmount()
  })

  it('updates the hash and renders the review list empty state', async () => {
    const { router, wrapper } = await mountTabs()

    await wrapper.get('#product-tab-reviews').trigger('click')
    await router.isReady()
    await flushPromises()

    expect(router.currentRoute.value.hash).toBe('#reviews')
    expect(wrapper.text()).toContain('Sản phẩm chưa có đánh giá')
    wrapper.unmount()
  })

  it('supports keyboard navigation across the tabs', async () => {
    const { router, wrapper } = await mountTabs()

    await wrapper.get('[role="tablist"]').trigger('keydown', { key: 'End' })
    await flushPromises()
    expect(router.currentRoute.value.hash).toBe('#reviews')
    expect(wrapper.get('#product-tab-reviews').attributes('aria-selected')).toBe('true')
    wrapper.unmount()
  })
})
