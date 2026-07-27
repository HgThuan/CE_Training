import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { sellerApi } from '../api'
import type { SellerApplication } from '../types'
import SellerApplicationPage from './SellerApplicationPage.vue'

vi.mock('../api', () => ({
  sellerApi: {
    getApplication: vi.fn(),
    submitApplication: vi.fn(),
    uploadDocument: vi.fn(),
  },
}))

const pendingApplication: SellerApplication = {
  id: 10,
  business_name: 'Future Shop',
  business_address: 'Hà Nội',
  tax_code: '0101234567',
  contact_phone: '0901234567',
  onboarding_status: 'pending',
  rejection_reason: '',
  verification_status: 'unverified',
  submitted_at: '2026-07-24T00:00:00Z',
  reviewed_at: null,
  documents: [],
  created_at: '2026-07-24T00:00:00Z',
  updated_at: '2026-07-24T00:00:00Z',
}

describe('SellerApplicationPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(sellerApi.getApplication).mockResolvedValue({
      data: { success: true, message: 'ok', data: null },
    } as Awaited<ReturnType<typeof sellerApi.getApplication>>)
  })

  it('submits step one without client-controlled identity and opens document step', async () => {
    vi.mocked(sellerApi.submitApplication).mockResolvedValue({
      data: { success: true, message: 'created', data: pendingApplication },
    } as Awaited<ReturnType<typeof sellerApi.submitApplication>>)
    const wrapper = mount(SellerApplicationPage, {
      global: {
        stubs: { FormMessage: { template: '<p><slot /></p>' } },
      },
    })
    await flushPromises()

    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('Future Shop')
    await inputs[1].setValue('0101234567')
    await inputs[2].setValue('0901234567')
    await wrapper.find('textarea').setValue('Hà Nội')
    await wrapper.get('[data-testid="application-form"]').trigger('submit')
    await flushPromises()

    expect(sellerApi.submitApplication).toHaveBeenCalledWith({
      business_name: 'Future Shop',
      business_address: 'Hà Nội',
      tax_code: '0101234567',
      contact_phone: '0901234567',
    })
    expect(wrapper.find('[data-testid="document-form"]').exists()).toBe(true)
  })
})
