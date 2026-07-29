import type { Banner } from './types'
import { bannersForPosition, moveBanner, reorderBanners } from './banner-order'

function banner(id: string, position: Banner['position'], sortOrder: number): Banner {
  return {
    id,
    title: id,
    image_url: `https://images.example.com/${id}.webp`,
    target_url: null,
    position,
    sort_order: sortOrder,
    starts_at: null,
    ends_at: null,
    is_active: true,
    created_at: '',
    updated_at: '',
  }
}

describe('admin banner ordering', () => {
  const banners = [
    banner('hero-b', 'hero', 1),
    banner('middle-a', 'middle', 0),
    banner('hero-a', 'hero', 0),
  ]

  it('sorts and normalizes banners within a position', () => {
    const ordered = bannersForPosition(banners, 'hero')
    expect(ordered.map((item) => item.id)).toEqual(['hero-a', 'hero-b'])
  })

  it('supports drag reorder and button fallback', () => {
    expect(reorderBanners(banners, 'hero-a', 'hero-b')?.map((item) => item.id)).toEqual([
      'hero-b',
      'hero-a',
    ])
    expect(moveBanner(banners, 'hero-b', -1)?.map((item) => item.id)).toEqual(['hero-b', 'hero-a'])
  })

  it('does not move a banner to another position', () => {
    expect(reorderBanners(banners, 'hero-a', 'middle-a')).toBeNull()
  })
})
