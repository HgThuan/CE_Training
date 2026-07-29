import { createPinia } from 'pinia'
import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { beforeEach, vi } from 'vitest'

import type { PublicProductListItem } from '@/features/product/types'

import { homeApi } from '../api'
import type { HomePageData } from '../types'
import HomePageContent from './HomePageContent.vue'

vi.mock('../api', () => ({
  homeApi: {
    get: vi.fn(),
  },
}))

const product: PublicProductListItem = {
  id: 'product-1',
  name: 'Điện thoại mới',
  slug: 'dien-thoai-moi',
  thumbnail: null,
  min_price: '4990000',
  max_price: '4990000',
  rating_average: '4.8',
  rating_count: 12,
  sold_count: 8,
  shop_name: 'Future Shop',
  shop_slug: 'future-shop',
}

const homeData: HomePageData = {
  banners: [
    {
      id: 'banner-1',
      title: 'Ưu đãi hôm nay',
      image_url: 'https://images.example.com/banner.webp',
      target_url: '/products',
      position: 'hero',
      sort_order: 0,
    },
  ],
  new_arrivals: [product],
  best_sellers: [],
  categories: [
    {
      id: 'category-1',
      name: 'Điện thoại',
      slug: 'dien-thoai',
      image_url: null,
    },
  ],
}

describe('HomePageContent', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(homeApi.get).mockResolvedValue({
      data: {
        success: true,
        message: 'Lấy trang chủ thành công',
        data: homeData,
      },
    } as Awaited<ReturnType<typeof homeApi.get>>)
  })

  it('renders banners, categories and product sections from the home API', async () => {
    const wrapper = mount(HomePageContent, {
      global: {
        plugins: [createPinia()],
        stubs: { RouterLink: RouterLinkStub },
      },
    })
    await flushPromises()

    expect(homeApi.get).toHaveBeenCalledOnce()
    expect(wrapper.text()).toContain('Ưu đãi hôm nay')
    expect(wrapper.text()).toContain('Điện thoại')
    expect(wrapper.text()).toContain('Điện thoại mới')
    expect(wrapper.text()).toContain('Danh sách bán chạy đang được cập nhật.')
    wrapper.unmount()
  })

  it('shows an error and retries the home request', async () => {
    vi.mocked(homeApi.get)
      .mockRejectedValueOnce(new Error('Mất kết nối'))
      .mockResolvedValueOnce({
        data: {
          success: true,
          message: 'Lấy trang chủ thành công',
          data: homeData,
        },
      } as Awaited<ReturnType<typeof homeApi.get>>)

    const wrapper = mount(HomePageContent, {
      global: {
        plugins: [createPinia()],
        stubs: { RouterLink: RouterLinkStub },
      },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('Mất kết nối')
    await wrapper.get('button').trigger('click')
    await flushPromises()

    expect(homeApi.get).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('Ưu đãi hôm nay')
    wrapper.unmount()
  })
})
