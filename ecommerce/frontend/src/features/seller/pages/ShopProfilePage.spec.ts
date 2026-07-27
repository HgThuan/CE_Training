import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { sellerApi } from '../api'
import type { Shop } from '../types'
import ShopProfilePage from './ShopProfilePage.vue'

vi.mock('../api', () => ({
  sellerApi: {
    getShop: vi.fn(),
    updateShop: vi.fn(),
    uploadShopImage: vi.fn(),
  },
}))

const shop: Shop = {
  id: 1,
  owner_id: 10,
  owner_email: 'seller@example.com',
  name: 'Future Shop',
  slug: 'future-shop',
  description: 'Shop description',
  logo_url: '/media/shops/10/logo.webp',
  cover_url: '/media/shops/10/cover.webp',
  logo_size: { width: 512, height: 512 },
  cover_size: { width: 1600, height: 480 },
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
    vi.stubGlobal('URL', {
      createObjectURL: vi.fn(() => 'blob:preview'),
    })
    vi.mocked(sellerApi.getShop).mockResolvedValue({
      data: { success: true, message: 'ok', data: shop },
    } as Awaited<ReturnType<typeof sellerApi.getShop>>)
    vi.mocked(sellerApi.uploadShopImage).mockResolvedValue({
      data: { success: true, message: 'uploaded', data: shop },
    } as Awaited<ReturnType<typeof sellerApi.uploadShopImage>>)
  })

  it('shows fixed image dimensions and uploads a logo file directly', async () => {
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

    const logoInput = wrapper.findAll('input[type="file"]')[0]
    const logo = new File(['image'], 'logo.png', { type: 'image/png' })
    Object.defineProperty(logoInput.element, 'files', { value: [logo] })
    await logoInput.trigger('change')
    await wrapper
      .findAll('button')
      .find((button) => button.text().includes('Tải logo'))!
      .trigger('click')
    await flushPromises()

    expect(sellerApi.uploadShopImage).toHaveBeenCalledWith('logo', logo)
  })
})
