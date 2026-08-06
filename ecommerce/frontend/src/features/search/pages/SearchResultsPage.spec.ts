import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, vi } from 'vitest'

import { productApi } from '@/features/product/api'
import type { Category, PublicProductListItem } from '@/features/product/types'

import { searchApi } from '../api'
import SearchResultsPage from './SearchResultsPage.vue'

vi.mock('../api', () => ({
  searchApi: {
    search: vi.fn(),
    suggestions: vi.fn(),
  },
}))

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
})
