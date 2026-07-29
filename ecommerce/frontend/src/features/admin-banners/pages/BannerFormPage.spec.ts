import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { beforeEach, vi } from 'vitest'

import { adminBannersApi } from '../api'
import type { Banner } from '../types'
import BannerFormPage from './BannerFormPage.vue'

const push = vi.fn()

vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('vue-router')>()
  return {
    ...actual,
    useRoute: () => ({ params: {} }),
    useRouter: () => ({ push }),
  }
})

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

const createdBanner: Banner = {
  id: 'banner-1',
  title: 'Banner mới',
  image_url: 'https://images.example.com/banner.webp',
  target_url: null,
  position: 'hero',
  sort_order: 0,
  starts_at: null,
  ends_at: null,
  is_active: true,
  created_at: '2026-07-29T00:00:00Z',
  updated_at: '2026-07-29T00:00:00Z',
}

describe('BannerFormPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(adminBannersApi.create).mockResolvedValue({
      data: {
        success: true,
        message: 'Tạo banner thành công',
        data: createdBanner,
      },
    } as Awaited<ReturnType<typeof adminBannersApi.create>>)
  })

  it('normalizes optional values and creates a URL-based banner', async () => {
    const wrapper = mount(BannerFormPage, {
      global: { stubs: { RouterLink: RouterLinkStub } },
    })

    await wrapper.get('input[maxlength="180"]').setValue('Banner mới')
    const urlInputs = wrapper.findAll('input[type="url"]')
    await urlInputs[0]!.setValue(createdBanner.image_url)
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(adminBannersApi.create).toHaveBeenCalledWith({
      title: 'Banner mới',
      image_url: createdBanner.image_url,
      target_url: null,
      position: 'hero',
      sort_order: 0,
      starts_at: null,
      ends_at: null,
      is_active: true,
    })
    expect(push).toHaveBeenCalledWith({
      path: '/admin/banners',
      query: { saved: 'created' },
    })
  })

  it('rejects an end time that is not after the start time', async () => {
    const wrapper = mount(BannerFormPage, {
      global: { stubs: { RouterLink: RouterLinkStub } },
    })

    await wrapper.findAll('input[type="url"]')[0]!.setValue(createdBanner.image_url)
    const dateInputs = wrapper.findAll('input[type="datetime-local"]')
    await dateInputs[0]!.setValue('2026-07-30T10:00')
    await dateInputs[1]!.setValue('2026-07-29T10:00')
    await wrapper.get('form').trigger('submit')

    expect(wrapper.text()).toContain('Thời gian kết thúc phải sau thời gian bắt đầu.')
    expect(adminBannersApi.create).not.toHaveBeenCalled()
  })
})
