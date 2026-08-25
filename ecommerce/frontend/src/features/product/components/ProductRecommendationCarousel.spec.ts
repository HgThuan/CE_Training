import { flushPromises, shallowMount } from '@vue/test-utils'
import { beforeEach, vi } from 'vitest'

import type { PublicProductListItem } from '../types'
import { trackRecommendationClick, trackRecommendationImpression } from '../recommendationTracking'
import ProductCard from './ProductCard.vue'
import ProductRecommendationCarousel from './ProductRecommendationCarousel.vue'

vi.mock('../recommendationTracking', () => ({
  trackRecommendationClick: vi.fn(),
  trackRecommendationImpression: vi.fn(),
}))

let intersectionCallback: IntersectionObserverCallback
let observedElements: Element[]
let unobservedElements: Element[]

class IntersectionObserverStub {
  constructor(callback: IntersectionObserverCallback) {
    intersectionCallback = callback
  }

  observe(element: Element) {
    observedElements.push(element)
  }

  unobserve(element: Element) {
    unobservedElements.push(element)
  }

  disconnect() {}
}

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
  beforeEach(() => {
    vi.clearAllMocks()
    observedElements = []
    unobservedElements = []
    vi.stubGlobal('IntersectionObserver', IntersectionObserverStub)
  })

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

  it('records one impression only after a recommendation is actually visible', async () => {
    const wrapper = shallowMount(ProductRecommendationCarousel, {
      props: {
        title: 'Gợi ý cho bạn',
        products: [product],
        recommendationId: '00000000-0000-4000-8000-000000000099',
        source: 'home',
      },
    })
    await flushPromises()

    expect(observedElements).toHaveLength(1)
    expect(trackRecommendationImpression).not.toHaveBeenCalled()

    const entry = {
      isIntersecting: true,
      intersectionRatio: 0.75,
      target: observedElements[0],
    } as IntersectionObserverEntry
    intersectionCallback([entry], {} as IntersectionObserver)
    intersectionCallback([entry], {} as IntersectionObserver)

    expect(trackRecommendationImpression).toHaveBeenCalledOnce()
    expect(trackRecommendationImpression).toHaveBeenCalledWith(
      '00000000-0000-4000-8000-000000000099',
      product.id,
      'home',
      0,
    )
    expect(unobservedElements).toEqual([observedElements[0]])
    wrapper.unmount()
  })

  it('keeps click attribution on the product card', async () => {
    const wrapper = shallowMount(ProductRecommendationCarousel, {
      props: {
        title: 'Gợi ý cho bạn',
        products: [product],
        recommendationId: '00000000-0000-4000-8000-000000000098',
        source: 'home',
      },
    })
    await flushPromises()

    await wrapper.getComponent(ProductCard).trigger('click')

    expect(trackRecommendationClick).toHaveBeenCalledWith(
      '00000000-0000-4000-8000-000000000098',
      product.id,
      'home',
      0,
    )
    wrapper.unmount()
  })
})
