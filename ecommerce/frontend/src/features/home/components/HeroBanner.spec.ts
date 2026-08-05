import { mount } from '@vue/test-utils'

import HeroBanner from './HeroBanner.vue'
import type { HomeBanner } from '../types'

const banners: HomeBanner[] = [
  {
    id: 'one',
    title: 'Ưu đãi mùa hè',
    image_url: 'https://images.example.com/one.webp',
    target_url: null,
    position: 'hero',
    sort_order: 0,
  },
  {
    id: 'two',
    title: 'Sản phẩm mới',  
    image_url: 'https://images.example.com/two.webp',
    target_url: '/products',
    position: 'hero',
    sort_order: 1,
  },
]

describe('HeroBanner', () => {
  it('moves through banners with accessible controls', async () => {
    const wrapper = mount(HeroBanner, { props: { banners } })

    expect(wrapper.text()).toContain('Ưu đãi mùa hè')
    await wrapper.get('button[aria-label="Banner tiếp theo"]').trigger('click')

    expect(wrapper.text()).toContain('Sản phẩm mới')
    expect(wrapper.get('a').attributes('href')).toBe('/products')
    wrapper.unmount()
  })
})
