import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { beforeEach, vi } from 'vitest'

import { adminBannersApi } from '../api'
import type { Banner } from '../types'
import BannerListPage from './BannerListPage.vue'

vi.mock('../api', () => ({
  adminBannersApi: {
    list: vi.fn(),
    detail: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    reorder: vi.fn(),
  },
}))

function banner(id: string, sortOrder: number): Banner {
  return {
    id,
    title: `Banner ${id}`,
    image_url: `https://images.example.com/${id}.webp`,
    target_url: null,
    position: 'hero',
    sort_order: sortOrder,
    starts_at: null,
    ends_at: null,
    is_active: true,
    created_at: '2026-07-29T00:00:00Z',
    updated_at: '2026-07-29T00:00:00Z',
  }
}

describe('BannerListPage', () => {
  const banners = [banner('one', 0), banner('two', 1)]

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(adminBannersApi.list).mockResolvedValue({
      data: { success: true, message: 'ok', data: banners },
    } as Awaited<ReturnType<typeof adminBannersApi.list>>)
    vi.mocked(adminBannersApi.reorder).mockResolvedValue({
      data: { success: true, message: 'Đã đổi thứ tự banner', data: banners },
    } as Awaited<ReturnType<typeof adminBannersApi.reorder>>)
  })

  it('uses the down button as a touch-friendly reorder fallback', async () => {
    const wrapper = mount(BannerListPage, {
      global: { stubs: { RouterLink: RouterLinkStub } },
    })
    await flushPromises()

    const downButtons = wrapper.findAll('button[aria-label="Đưa banner xuống"]')
    await downButtons[0]!.trigger('click')
    await flushPromises()

    expect(adminBannersApi.reorder).toHaveBeenCalledWith('one', 'two')
    expect(adminBannersApi.list).toHaveBeenCalledTimes(2)
    expect(wrapper.text()).toContain('Đã đổi thứ tự banner')
  })
})
