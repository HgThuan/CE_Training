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

  it('normalizes a cleared optional birth date before creating a customer', async () => {
    vi.mocked(adminUsersApi.createCustomer).mockResolvedValue({
      data: {
        success: true,
        message: 'Tạo khách hàng thành công',
        data: {
          id: 8,
          email: 'new@example.com',
          full_name: 'New Customer',
          phone: '',
          is_active: true,
          is_email_verified: false,
          must_change_password: false,
          created_at: '2026-07-23T00:00:00Z',
        },
      },
    } as Awaited<ReturnType<typeof adminUsersApi.createCustomer>>)
    const wrapper = mount(CustomerManagementPage, {
      global: { stubs: { RouterLink: RouterLinkStub } },
    })
    await flushPromises()

    const createToggle = wrapper
      .findAll('button')
      .find((button) => button.text() === 'Tạo khách hàng')
    await createToggle?.trigger('click')
    const createForm = wrapper.findAll('form')[0]
    await createForm.get('input[type="email"]').setValue('new@example.com')
    await createForm.get('input:not([type])').setValue('New Customer')
    await createForm.get('input[type="date"]').setValue('2000-01-01')
    await createForm.get('input[type="date"]').setValue('')
    const passwordInputs = createForm.findAll('input[type="password"]')
    await passwordInputs[0].setValue('StrongPass!234')
    await passwordInputs[1].setValue('StrongPass!234')
    await createForm.trigger('submit')
    await flushPromises()

    expect(adminUsersApi.createCustomer).toHaveBeenCalledWith(
      expect.objectContaining({
        email: 'new@example.com',
        date_of_birth: null,
      }),
    )
  })
})
