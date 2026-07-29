import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, vi } from 'vitest'

import { productApi } from '@/features/product/api'
import type { Category, PublicProductListItem } from '@/features/product/types'

import { searchApi } from '../api'
import SearchResultsPage from './SearchResultsPage.vue'

vi.mock('../api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api')>()
  return {
    ...actual,
    searchApi: {
      search: vi.fn(),
      smartSearch: vi.fn(),
      suggestions: vi.fn(),
    },
  }
})

vi.mock('@/features/product/api', () => ({
  productApi: {
    list: vi.fn(),
    detail: vi.fn(),
    categories: vi.fn(),
    brands: vi.fn(),
  },
}))

const category: Category = {
  id: 'category-1',
  parent_id: null,
  name: 'Điện thoại',
  slug: 'dien-thoai',
  image_url: null,
  sort_order: 0,
  is_active: true,
  children: [],
  created_at: '',
  updated_at: '',
}

const product: PublicProductListItem = {
  id: 'product-1',
  name: 'Điện thoại chống nước',
  slug: 'dien-thoai-chong-nuoc',
  thumbnail: null,
  min_price: '4900000',
  max_price: '4900000',
  rating_average: '4.8',
  rating_count: 20,
  sold_count: 12,
  shop_name: 'Future Shop',
  shop_slug: 'future-shop',
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((promiseResolve) => {
    resolve = promiseResolve
  })
  return { promise, resolve }
}

async function mountPage(url: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/search', component: SearchResultsPage }],
  })
  await router.push(url)
  await router.isReady()
  return {
    router,
    wrapper: mount(SearchResultsPage, {
      global: {
        plugins: [createPinia(), router],
        stubs: {
          ProductCard: {
            props: ['product'],
            template: '<article>{{ product.name }}</article>',
          },
        },
      },
    }),
  }
}

describe('SearchResultsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(productApi.categories).mockResolvedValue({
      data: { success: true, message: 'ok', data: [category] },
    } as unknown as Awaited<ReturnType<typeof productApi.categories>>)
    vi.mocked(productApi.brands).mockResolvedValue({
      data: { success: true, message: 'ok', data: [] },
    } as unknown as Awaited<ReturnType<typeof productApi.brands>>)
    vi.mocked(searchApi.search).mockResolvedValue({
      data: {
        success: true,
        message: 'ok',
        data: [product],
        meta: { page: 1, page_size: 12, total_items: 1, total_pages: 1 },
      },
    } as unknown as Awaited<ReturnType<typeof searchApi.search>>)
    vi.mocked(searchApi.smartSearch).mockResolvedValue({
      data: {
        success: true,
        message: 'ok',
        data: {
          results: [product],
          explanation: 'Kết quả phù hợp với nhu cầu của bạn.',
          intent: { keywords: ['điện thoại'], filters: {} },
          ai_used: true,
          fallback_used: false,
        },
        meta: { page: 1, page_size: 12, total_items: 1, total_pages: 1 },
      },
    } as unknown as Awaited<ReturnType<typeof searchApi.smartSearch>>)
  })

  it('hydrates filters from the URL and renders API results', async () => {
    const { wrapper } = await mountPage('/search?q=dien+thoai&rating_min=4&in_stock=true')
    await flushPromises()

    expect(searchApi.search).toHaveBeenCalledWith(
      expect.objectContaining({
        q: 'dien thoai',
        rating_min: 4,
        in_stock: true,
        page: 1,
        page_size: 12,
      }),
    )
    expect(wrapper.text()).toContain('Điện thoại chống nước')
    expect(wrapper.text()).toContain('Kết quả cho “dien thoai”')
  })

  it('writes applied filters back to the URL and reloads', async () => {
    const { router, wrapper } = await mountPage('/search?q=dien')
    await flushPromises()
    const filterForm = wrapper.get('form[aria-label="Bộ lọc tìm kiếm"]')

    await filterForm.get('select').setValue(category.id)
    await filterForm.get('input[type="checkbox"]').setValue(true)
    await filterForm.trigger('submit')
    await flushPromises()

    expect(router.currentRoute.value.query.category).toBe(category.id)
    expect(router.currentRoute.value.query.in_stock).toBe('true')
    expect(searchApi.search).toHaveBeenLastCalledWith(
      expect.objectContaining({
        q: 'dien',
        category: category.id,
        in_stock: true,
      }),
    )
  })

  it('toggles AI mode without losing filters and resets pagination', async () => {
    const { router, wrapper } = await mountPage(
      '/search?q=dien&category=category-1&sort=-price&page=2',
    )
    await flushPromises()

    await wrapper.get('input[role="switch"][aria-label="AI Search"]').setValue(true)
    await flushPromises()

    expect(router.currentRoute.value.query).toMatchObject({
      q: 'dien',
      category: 'category-1',
      sort: '-price',
      ai: 'true',
    })
    expect(router.currentRoute.value.query.page).toBeUndefined()
    expect(searchApi.smartSearch).toHaveBeenCalledWith(
      expect.objectContaining({
        q: 'dien',
        category: 'category-1',
        sort: '-price',
        page: 1,
      }),
    )
  })

  it('uses AI search, accepts the products alias and preserves filters when sorting', async () => {
    vi.mocked(searchApi.smartSearch).mockResolvedValueOnce({
      data: {
        success: true,
        message: 'ok',
        data: {
          products: [product],
          explanation: 'Ưu tiên điện thoại chống nước trong tầm giá.',
          intent: { keywords: ['điện thoại', 'chống nước'], filters: { rating_min: 4 } },
          ai_used: true,
          fallback_used: false,
        },
        meta: { page: 2, page_size: 12, total_items: 13, total_pages: 2 },
      },
    } as unknown as Awaited<ReturnType<typeof searchApi.smartSearch>>)

    const { router, wrapper } = await mountPage(
      '/search?q=dien+thoai&ai=true&rating_min=4&sort=-price&page=2',
    )
    await flushPromises()

    expect(searchApi.smartSearch).toHaveBeenCalledWith(
      expect.objectContaining({
        q: 'dien thoai',
        rating_min: 4,
        sort: '-price',
        page: 2,
      }),
    )
    expect(searchApi.search).not.toHaveBeenCalled()
    expect(wrapper.get('[data-testid="ai-result-badge"]').text()).toBe('AI')
    expect(wrapper.text()).toContain('Ưu tiên điện thoại chống nước trong tầm giá.')
    expect(wrapper.text()).toContain('Điện thoại chống nước')

    await wrapper.get('select[aria-label="Sắp xếp kết quả"]').setValue('price')
    await flushPromises()

    expect(router.currentRoute.value.query.ai).toBe('true')
    expect(router.currentRoute.value.query.rating_min).toBe('4')
    expect(router.currentRoute.value.query.sort).toBe('price')
  })

  it('falls back to keyword search when AI search is unavailable', async () => {
    vi.mocked(searchApi.smartSearch).mockRejectedValueOnce(new Error('AI unavailable'))

    const { wrapper } = await mountPage('/search?q=dien+thoai&ai=true')
    await flushPromises()

    expect(searchApi.smartSearch).toHaveBeenCalledOnce()
    expect(searchApi.search).toHaveBeenCalledOnce()
    expect(wrapper.text()).toContain('AI Search tạm thời không khả dụng')
    expect(wrapper.text()).toContain('Điện thoại chống nước')
    expect(wrapper.find('[data-testid="ai-result-badge"]').exists()).toBe(false)
  })

  it('renders backend fallback results without claiming they were generated by AI', async () => {
    vi.mocked(searchApi.smartSearch).mockResolvedValueOnce({
      data: {
        success: true,
        message: 'fallback',
        data: {
          results: [product],
          explanation: '',
          intent: { keywords: ['điện thoại'], filters: {} },
          ai_used: false,
          fallback_used: true,
        },
        meta: { page: 1, page_size: 12, total_items: 1, total_pages: 1 },
      },
    } as unknown as Awaited<ReturnType<typeof searchApi.smartSearch>>)

    const { wrapper } = await mountPage('/search?q=dien+thoai&ai=true')
    await flushPromises()

    expect(searchApi.search).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Kết quả dự phòng')
    expect(wrapper.text()).toContain('AI Search đã chuyển sang tìm kiếm từ khóa')
    expect(wrapper.find('[data-testid="ai-result-badge"]').exists()).toBe(false)
  })

  it('ignores a stale AI response after switching back to keyword search', async () => {
    const pendingAi = deferred<Awaited<ReturnType<typeof searchApi.smartSearch>>>()
    const staleProduct: PublicProductListItem = {
      ...product,
      id: 'stale-product',
      name: 'Kết quả AI đã cũ',
    }
    vi.mocked(searchApi.smartSearch).mockImplementationOnce(() => pendingAi.promise)

    const { wrapper } = await mountPage('/search?q=dien+thoai&ai=true')
    await flushPromises()
    await wrapper.get('input[role="switch"][aria-label="AI Search"]').setValue(false)
    await flushPromises()

    expect(wrapper.text()).toContain('Điện thoại chống nước')
    expect(searchApi.search).toHaveBeenCalledOnce()

    pendingAi.resolve({
      data: {
        success: true,
        message: 'ok',
        data: {
          results: [staleProduct],
          explanation: 'Phản hồi cũ không được hiển thị.',
          intent: { keywords: ['cũ'], filters: {} },
          ai_used: true,
          fallback_used: false,
        },
        meta: { page: 1, page_size: 12, total_items: 1, total_pages: 1 },
      },
    } as unknown as Awaited<ReturnType<typeof searchApi.smartSearch>>)
    await flushPromises()

    expect(wrapper.text()).not.toContain('Kết quả AI đã cũ')
    expect(wrapper.text()).not.toContain('Phản hồi cũ không được hiển thị.')
    expect(wrapper.find('[data-testid="ai-result-badge"]').exists()).toBe(false)
  })
})
