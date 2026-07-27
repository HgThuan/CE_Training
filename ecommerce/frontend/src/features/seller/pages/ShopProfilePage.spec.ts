import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { sellerApi } from '../api'
import type { Shop } from '../types'
import ShopProfilePage from './ShopProfilePage.vue'

vi.mock('../api', () => ({
  sellerApi: {
    getShop: vi.fn(),
    updateShop: vi.fn(),
  },
}))

const shop: Shop = {
  id: 1,
  owner_id: 10,
  owner_email: 'seller@example.com',
  name: 'Future Shop',
  slug: 'future-shop',
  description: 'Shop description',
  logo_url: 'https://cdn.example.com/shops/10/logo.webp',
  cover_url: 'https://cdn.example.com/shops/10/cover.webp',
  status: 'approved',
  lock_reason: '',
  locked_at: null,
  average_rating: '0.00',
  total_products: 0,
  created_at: '2026-07-24T00:00:00Z',
  updated_at: '2026-07-24T00:00:00Z',
}

describe('ShopProfilePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(sellerApi.getShop).mockResolvedValue({
      data: { success: true, message: 'ok', data: shop },
    } as Awaited<ReturnType<typeof sellerApi.getShop>>)
    vi.mocked(sellerApi.updateShop).mockResolvedValue({
      data: { success: true, message: 'updated', data: shop },
    } as Awaited<ReturnType<typeof sellerApi.updateShop>>)
  })

  it('loads logo and cover URLs and saves them with the shop profile', async () => {
    const wrapper = mount(ShopProfilePage, {
      global: {
        stubs: {
          RouterLink: { template: '<a><slot /></a>' },
          FormMessage: { template: '<p />' },
        },
      },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('512 × 512 px')
    expect(wrapper.text()).toContain('1600 × 480 px')

    const logoUrl = 'https://images.example.com/new-logo.webp'
    await wrapper.find('input[name="logo_url"]').setValue(logoUrl)
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(sellerApi.updateShop).toHaveBeenCalledWith({
      name: shop.name,
      description: shop.description,
      logo_url: logoUrl,
      cover_url: shop.cover_url,
    })
  })
})
