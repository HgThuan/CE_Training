import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { SellerApplication, SellerDocument } from '@/features/seller/types'

import { adminSellersApi } from '../api'
import SellerApprovalPage from './SellerApprovalPage.vue'

vi.mock('../api', () => ({
  adminSellersApi: {
    listApplications: vi.fn(),
    getApplication: vi.fn(),
    approveApplication: vi.fn(),
    rejectApplication: vi.fn(),
    reviewDocument: vi.fn(),
  },
}))

const document: SellerDocument = {
  id: 21,
  document_type: 'business_license',
  file_url: '/protected-media/document',
  original_name: 'business-license.pdf',
  review_status: 'pending',
  review_reason: '',
  reviewed_at: null,
  created_at: '2026-07-24T00:00:00Z',
  updated_at: '2026-07-24T00:00:00Z',
}

const application: SellerApplication = {
  id: 10,
  business_name: 'Future Shop',
  business_address: 'Hà Nội',
  tax_code: '0101234567',
  contact_phone: '0901234567',
  onboarding_status: 'pending',
  rejection_reason: '',
  verification_status: 'pending',
  submitted_at: '2026-07-24T00:00:00Z',
  reviewed_at: null,
  documents: [document],
  created_at: '2026-07-24T00:00:00Z',
  updated_at: '2026-07-24T00:00:00Z',
}

async function mountSelectedApplication() {
  const wrapper = mount(SellerApprovalPage, {
    global: { stubs: { RouterLink: RouterLinkStub } },
  })
  await flushPromises()

  await wrapper
    .findAll('button')
    .find((button) => button.text().includes(application.business_name))
    ?.trigger('click')
  await flushPromises()

  return wrapper
}

describe('SellerApprovalPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(adminSellersApi.listApplications).mockResolvedValue({
      data: {
        success: true,
        message: 'ok',
        data: [application],
        meta: { page: 1, page_size: 20, total_items: 1, total_pages: 1 },
      },
    } as Awaited<ReturnType<typeof adminSellersApi.listApplications>>)
    vi.mocked(adminSellersApi.getApplication).mockResolvedValue({
      data: { success: true, message: 'ok', data: application },
    } as Awaited<ReturnType<typeof adminSellersApi.getApplication>>)
    vi.mocked(adminSellersApi.reviewDocument).mockResolvedValue({
      data: { success: true, message: 'updated', data: document },
    } as Awaited<ReturnType<typeof adminSellersApi.reviewDocument>>)
  })

  it('renders status choices from configuration and applies the selected filter', async () => {
    const wrapper = mount(SellerApprovalPage, {
      global: { stubs: { RouterLink: RouterLinkStub } },
    })
    await flushPromises()

    const statusSelect = wrapper.get('select[aria-label="Trạng thái hồ sơ"]')
    expect(
      statusSelect.findAll('option').map((option) => ({
        value: option.attributes('value'),
        label: option.text(),
      })),
    ).toEqual([
      { value: 'pending', label: 'Chờ duyệt' },
      { value: 'approved', label: 'Đã duyệt' },
      { value: 'rejected', label: 'Từ chối' },
    ])

    await statusSelect.setValue('rejected')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(adminSellersApi.listApplications).toHaveBeenLastCalledWith(
      expect.objectContaining({ onboarding_status: 'rejected', page: 1 }),
    )
  })

  it('sends the verified status without a reason', async () => {
    const wrapper = await mountSelectedApplication()

    await wrapper
      .findAll('button')
      .find((button) => button.text() === 'Xác minh')
      ?.trigger('click')
    await flushPromises()

    expect(adminSellersApi.reviewDocument).toHaveBeenCalledWith(document.id, 'verified', '')
  })

  it('requires and trims a reason when requesting additional information', async () => {
    const wrapper = await mountSelectedApplication()

    await wrapper
      .findAll('button')
      .find((button) => button.text() === 'Yêu cầu bổ sung')
      ?.trigger('click')
    await wrapper.get('input[placeholder="Nhập nội dung..."]').setValue('  Thiếu con dấu  ')
    await wrapper
      .findAll('button')
      .find((button) => button.text() === 'Xác nhận')
      ?.trigger('click')
    await flushPromises()

    expect(adminSellersApi.reviewDocument).toHaveBeenCalledWith(
      document.id,
      'additional_required',
      'Thiếu con dấu',
    )
  })
})
