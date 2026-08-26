import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useCartStore } from '@/features/cart/store'

import { promotionApi } from '../api'
import type { FlashSaleItem } from '../types'
import FlashSaleBanner from './FlashSaleBanner.vue'

vi.mock('../api', () => ({
  promotionApi: { activeFlashSales: vi.fn() },
}))

function flashItem(overrides: Partial<FlashSaleItem> = {}): FlashSaleItem {
  return {
    id: 'flash-item-1',
    variant: 'variant-1',
    product_name: 'Chuột không dây',
    product_slug: 'chuot-khong-day',
    shop_slug: 'tech-shop',
    variant_sku: 'MOUSE-BLACK',
    primary_image: null,
    original_price: '100000',
    sale_price: '80000',
    quota: 10,
    sold_count: 2,
    remaining_quota: 8,
    available_stock: 7,
    ...overrides,
  }
}

async function mountBanner(item: FlashSaleItem) {
  const pinia = createPinia()
  setActivePinia(pinia)
  vi.mocked(promotionApi.activeFlashSales).mockResolvedValue({
    data: {
      success: true,
      message: 'ok',
      data: [
        {
          id: 'sale-1',
          name: 'Giờ vàng',
          start_time: '2026-08-26T00:00:00Z',
          end_time: '2099-08-26T01:00:00Z',
          is_active: true,
          status: 'ongoing',
          items: [item],
          created_at: '2026-08-26T00:00:00Z',
          updated_at: '2026-08-26T00:00:00Z',
        },
      ],
    },
  } as never)
  const cartStore = useCartStore()
  const addItem = vi.spyOn(cartStore, 'addItem').mockResolvedValue()
  const wrapper = mount(FlashSaleBanner, {
    global: {
      plugins: [pinia],
      stubs: { RouterLink: { template: '<a><slot /></a>' } },
    },
  })
  await flushPromises()
  return { addItem, wrapper }
}

describe('FlashSaleBanner', () => {
  beforeEach(() => vi.clearAllMocks())

  it('disables adding when the current inventory is exhausted', async () => {
    const { addItem, wrapper } = await mountBanner(flashItem({ available_stock: 0 }))
    const button = wrapper.get('button')

    expect(button.attributes('disabled')).toBeDefined()
    expect(button.text()).toContain('Hết hàng')
    await button.trigger('click')
    expect(addItem).not.toHaveBeenCalled()
  })

  it('passes the shop context when adding a purchasable item', async () => {
    const { addItem, wrapper } = await mountBanner(flashItem())

    await wrapper.get('button').trigger('click')
    await flushPromises()

    expect(addItem).toHaveBeenCalledWith(
      'variant-1',
      1,
      expect.objectContaining({
        product_slug: 'chuot-khong-day',
        shop_slug: 'tech-shop',
      }),
    )
  })
})
