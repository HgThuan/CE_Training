import { createPinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'

import type { PublicProductListItem } from '../types'
import ProductCard from './ProductCard.vue'

const product: PublicProductListItem = {
  id: 'product-1',
  name: 'Điện thoại',
  slug: 'dien-thoai',
  thumbnail: 'https://images.example.com/product.webp',
  min_price: '100000',
  max_price: '100000',
  rating_average: '4.8',
  rating_count: 10,
  sold_count: 20,
  shop_name: 'Future Shop',
  shop_slug: 'future-shop',
}

describe('ProductCard', () => {
  it('shows the effective Flash Sale price on the shared product card', () => {
    const wrapper = mount(ProductCard, {
      props: {
        product: {
          ...product,
          min_price: '70000',
          max_price: '70000',
          regular_min_price: '100000',
          regular_max_price: '100000',
          is_flash_sale: true,
          flash_sale_ends_at: '2026-08-03T12:00:00Z',
        },
      },
      global: {
        stubs: {
          RouterLink: { template: '<a><slot /></a>' },
          WishlistToggleButton: true,
        },
      },
    })

    expect(wrapper.text()).toContain('FLASH SALE')
    expect(wrapper.text()).toContain('70.000')
    expect(wrapper.text()).toContain('100.000')
  })

  it('keeps the wishlist button outside the product link and preserves lazy images', async () => {
    const component = { template: '<div />' }
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/products', component },
        { path: '/products/:slug', name: 'product-detail', component },
        { path: '/auth/login', name: 'login', component },
      ],
    })
    await router.push('/products')
    await router.isReady()
    const wrapper = mount(ProductCard, {
      props: { product },
      global: { plugins: [createPinia(), router] },
    })

    expect(wrapper.find('a button').exists()).toBe(false)
    expect(wrapper.find('article > button').exists()).toBe(true)
    expect(wrapper.get('img').attributes('loading')).toBe('lazy')

    await wrapper.get('article > button').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.name).toBe('login')
    wrapper.unmount()
  })
})
