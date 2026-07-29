import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'

import type { ProductMedia } from '../types'
import ProductGallery from './ProductGallery.vue'

const media: ProductMedia[] = [
  {
    id: 'image-1',
    variant_id: null,
    media_type: 'image',
    file_url: 'https://images.example.com/front.webp',
    thumbnail_url: 'https://images.example.com/front-thumb.webp',
    alt_text: 'Mặt trước',
    sort_order: 0,
    is_primary: true,
    created_at: '2026-07-01T00:00:00Z',
  },
  {
    id: 'video-1',
    variant_id: null,
    media_type: 'video',
    file_url: 'https://images.example.com/demo.mp4',
    thumbnail_url: 'https://images.example.com/demo-thumb.webp',
    alt_text: null,
    sort_order: 1,
    is_primary: false,
    created_at: '2026-07-01T00:00:00Z',
  },
  {
    id: 'image-2',
    variant_id: null,
    media_type: 'image',
    file_url: 'https://images.example.com/back.webp',
    thumbnail_url: null,
    alt_text: 'Mặt sau',
    sort_order: 2,
    is_primary: false,
    created_at: '2026-07-01T00:00:00Z',
  },
]

describe('ProductGallery', () => {
  it('loads thumbnails lazily while prioritizing the active image', () => {
    const wrapper = mount(ProductGallery, {
      props: { media, productName: 'Điện thoại' },
    })

    expect(
      wrapper.get('button[aria-label="Phóng to ảnh sản phẩm"] img').attributes('loading'),
    ).toBe('eager')
    const thumbnails = wrapper.findAll('button[aria-label^="Xem media"] img')
    expect(thumbnails).toHaveLength(3)
    expect(thumbnails.every((thumbnail) => thumbnail.attributes('loading') === 'lazy')).toBe(true)
    wrapper.unmount()
  })

  it('opens a lightbox, skips videos during image navigation and restores page scrolling', async () => {
    const wrapper = mount(ProductGallery, {
      props: { media, productName: 'Điện thoại' },
    })

    await wrapper.get('button[aria-label="Phóng to ảnh sản phẩm"]').trigger('click')
    expect(document.body.style.overflow).toBe('hidden')
    expect(document.body.querySelector('[role="dialog"]')).not.toBeNull()

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight' }))
    await nextTick()
    expect(document.body.querySelector('[role="dialog"] img')?.getAttribute('src')).toBe(
      media[2]!.file_url,
    )

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await nextTick()
    expect(document.body.querySelector('[role="dialog"]')).toBeNull()
    expect(document.body.style.overflow).toBe('')
    wrapper.unmount()
  })

  it('supports video in the regular media carousel', async () => {
    const wrapper = mount(ProductGallery, {
      props: { media, productName: 'Điện thoại' },
    })

    await wrapper.get('button[aria-label="Media tiếp theo"]').trigger('click')
    expect(wrapper.get('video').attributes('preload')).toBe('metadata')
    expect(wrapper.get('video').attributes('poster')).toBe(media[1]!.thumbnail_url)
    wrapper.unmount()
  })
})
