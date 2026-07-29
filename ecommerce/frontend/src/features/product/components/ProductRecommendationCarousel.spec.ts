import { shallowMount } from '@vue/test-utils'

import type { PublicProductListItem } from '../types'
import ProductCard from './ProductCard.vue'
import ProductRecommendationCarousel from './ProductRecommendationCarousel.vue'

const product: PublicProductListItem = {
  id: '00000000-0000-4000-8000-000000000001',
  name: 'Điện thoại gợi ý',
  slug: 'dien-thoai-goi-y',
  thumbnail: null,
  min_price: '4990000',
  max_price: '4990000',
  rating_average: '4.8',
  rating_count: 12,
  sold_count: 8,
  shop_name: 'Future Shop',
  shop_slug: 'future-shop',
}

describe('ProductRecommendationCarousel', () => {
  it('hides the section when it is neither loading nor populated', () => {
    const wrapper = shallowMount(ProductRecommendationCarousel, {
      props: {
        title: 'Sản phẩm tương tự',
        products: [],
      },
    })

    expect(wrapper.find('section').exists()).toBe(false)
  })

  it('renders an accessible skeleton while loading', () => {
    const wrapper = shallowMount(ProductRecommendationCarousel, {
      props: {
        title: 'Gợi ý cho bạn',
        products: [],
        loading: true,
      },
    })

    expect(wrapper.get('section').attributes('aria-busy')).toBe('true')
    expect(wrapper.get('[role="status"]').text()).toContain('Đang tải')
    expect(wrapper.findAll('li')).toHaveLength(4)
    expect(wrapper.findComponent(ProductCard).exists()).toBe(false)
  })

  it('labels the product list and uses responsive, horizontally snapping cards', () => {
    const wrapper = shallowMount(ProductRecommendationCarousel, {
      props: {
        title: 'Sản phẩm tương tự',
        products: [product],
      },
    })

    const section = wrapper.get('section')
    const heading = wrapper.get('h2')
    const list = wrapper.get('ul')
    const item = wrapper.get('li')

    expect(section.attributes('aria-labelledby')).toBe(heading.attributes('id'))
    expect(section.attributes('aria-busy')).toBe('false')
    expect(list.attributes('aria-label')).toBe('Sản phẩm tương tự')
    expect(list.classes()).toEqual(expect.arrayContaining(['overflow-x-auto', 'snap-x']))
    expect(item.classes()).toEqual(
      expect.arrayContaining([
        'w-[78vw]',
        'sm:w-72',
        'lg:w-[calc(25%-0.9375rem)]',
        'shrink-0',
        'snap-start',
      ]),
    )
    expect(wrapper.findAllComponents(ProductCard)).toHaveLength(1)
  })
})
