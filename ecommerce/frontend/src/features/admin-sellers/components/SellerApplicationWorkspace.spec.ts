import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, vi } from 'vitest'

import type { SellerApplication } from '@/features/seller/types'
import { adminSellersApi } from '../api'
import SellerApplicationWorkspace from './SellerApplicationWorkspace.vue'

vi.mock('../api', () => ({
  adminSellersApi: {
    listApplications: vi.fn(),
    getApplication: vi.fn(),
    approveApplication: vi.fn(),
    rejectApplication: vi.fn(),
    reviewDocument: vi.fn(),
  },
}))

vi.mock('@/shared/composables/useAppDialog', () => ({
  confirmDialog: vi.fn(),
  promptDialog: vi.fn(),
}))

const application: SellerApplication = {
  id: 17,
  business_name: 'Công ty Mercato',
  business_address: 'Hà Nội',
  tax_code: '0101234567',
  contact_phone: '0901234567',
  onboarding_status: 'pending',
  rejection_reason: '',
  verification_status: 'pending',
  submitted_at: '2026-08-14T01:00:00Z',
  reviewed_at: null,
  documents: [],
  created_at: '2026-08-14T01:00:00Z',
  updated_at: '2026-08-14T01:00:00Z',
}

describe('SellerApplicationWorkspace', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(adminSellersApi.listApplications).mockResolvedValue({
      data: {
        success: true,
        message: 'ok',
        data: [application],
        meta: { page: 1, page_size: 12, total_items: 1, total_pages: 1 },
      },
    } as Awaited<ReturnType<typeof adminSellersApi.listApplications>>)
    vi.mocked(adminSellersApi.getApplication).mockResolvedValue({
      data: { success: true, message: 'ok', data: application },
    } as Awaited<ReturnType<typeof adminSellersApi.getApplication>>)
  })

  it('requests a compact page of twelve applications', async () => {
    mount(SellerApplicationWorkspace, { props: { status: 'pending' } })
    await flushPromises()
    expect(adminSellersApi.listApplications).toHaveBeenCalledWith({
      search: undefined,
      onboarding_status: 'pending',
      page: 1,
      page_size: 12,
    })
  })

  it('switches between the list and detail workspace on narrow screens', async () => {
    const wrapper = mount(SellerApplicationWorkspace, { props: { status: 'pending' } })
    await flushPromises()
    await wrapper.get('button[type="button"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Quay lại danh sách')
    expect(wrapper.get('[aria-label="Danh sách hồ sơ seller"]').classes()).toContain('hidden')
    await wrapper.get('button.xl\\:hidden').trigger('click')
    expect(wrapper.get('[aria-label="Danh sách hồ sơ seller"]').classes()).toContain('flex')
  })
})
