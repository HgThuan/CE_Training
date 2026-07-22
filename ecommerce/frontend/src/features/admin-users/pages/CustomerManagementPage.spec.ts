import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { adminUsersApi } from '../api'
import CustomerManagementPage from './CustomerManagementPage.vue'

vi.mock('../api', () => ({
  adminUsersApi: {
    listCustomers: vi.fn(),
    getCustomer: vi.fn(),
    createCustomer: vi.fn(),
    updateCustomer: vi.fn(),
    deleteCustomer: vi.fn(),
    lockUser: vi.fn(),
    unlockUser: vi.fn(),
    resetPassword: vi.fn(),
  },
}))

describe('CustomerManagementPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(adminUsersApi.listCustomers).mockResolvedValue({
      data: {
        success: true,
        message: 'ok',
        data: [
          {
            id: 7,
            email: 'customer@example.com',
            full_name: 'Test Customer',
            phone: '0901234567',
            is_active: true,
            is_email_verified: true,
            must_change_password: false,
            created_at: '2026-01-01T00:00:00Z',
          },
        ],
        meta: { page: 1, page_size: 20, total_items: 1, total_pages: 1 },
      },
    } as Awaited<ReturnType<typeof adminUsersApi.listCustomers>>)
  })

  it('loads the paginated customer list and applies a search', async () => {
    const wrapper = mount(CustomerManagementPage, {
      global: { stubs: { RouterLink: RouterLinkStub } },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('Test Customer')
    expect(wrapper.text()).toContain('customer@example.com')

    await wrapper.get('input[aria-label="Tìm khách hàng"]').setValue('Test')
    await wrapper.get('section form').trigger('submit')
    await flushPromises()

    expect(adminUsersApi.listCustomers).toHaveBeenLastCalledWith(
      expect.objectContaining({ search: 'Test', page: 1 }),
    )
  })
})
