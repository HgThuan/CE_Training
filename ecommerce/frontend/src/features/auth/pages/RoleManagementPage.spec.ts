import { createPinia, setActivePinia, type Pinia } from 'pinia'
import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { analyticsApi } from '@/features/analytics/api'
import { confirmDialog } from '@/shared/composables/useAppDialog'
import { useAuthStore } from '@/stores/auth'

import { authApi } from '../api'
import type { AuthenticatedUser, RoleAssignableUser } from '../types'
import RoleManagementPage from './RoleManagementPage.vue'

vi.mock('../api', () => ({
  authApi: {
    roleUsers: vi.fn(),
    assignRole: vi.fn(),
  },
}))

vi.mock('@/features/analytics/api', () => ({
  analyticsApi: { auditLogs: vi.fn() },
}))

vi.mock('@/shared/composables/useAppDialog', () => ({
  confirmDialog: vi.fn(),
}))

const targetUser: RoleAssignableUser = {
  id: 17,
  email: 'target@example.com',
  full_name: 'Nguyễn Văn Target',
  phone: '0901234567',
  role: 'customer',
  is_active: true,
}

const adminUser: RoleAssignableUser = {
  ...targetUser,
  id: 18,
  email: 'admin-target@example.com',
  full_name: '',
  role: 'admin',
}

function authenticatedUser(id = 99): AuthenticatedUser {
  return {
    id,
    email: 'current-admin@example.com',
    role: 'admin',
    is_active: true,
    is_email_verified: true,
    must_change_password: false,
    avatar_url: '',
    full_name: 'Current Admin',
    phone: '',
    date_of_birth: null,
    gender: '',
    profile: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  }
}

function listResponse(users: RoleAssignableUser[], page = 1, totalPages = 1) {
  return {
    data: {
      success: true,
      message: 'ok',
      data: users,
      meta: {
        page,
        page_size: 20,
        total_items: totalPages > 1 ? 25 : users.length,
        total_pages: totalPages,
      },
    },
  } as Awaited<ReturnType<typeof authApi.roleUsers>>
}

function mountPage(pinia: Pinia) {
  return mount(RoleManagementPage, {
    global: {
      plugins: [pinia],
      stubs: { RouterLink: RouterLinkStub },
    },
  })
}

describe('RoleManagementPage', () => {
  let pinia: Pinia

  beforeEach(() => {
    vi.clearAllMocks()
    pinia = createPinia()
    setActivePinia(pinia)
    useAuthStore().$patch({ user: authenticatedUser() })
    vi.mocked(authApi.roleUsers).mockResolvedValue(listResponse([targetUser]))
    vi.mocked(analyticsApi.auditLogs).mockResolvedValue({
      data: { success: true, message: 'ok', data: [] },
    } as unknown as Awaited<ReturnType<typeof analyticsApi.auditLogs>>)
    vi.mocked(confirmDialog).mockResolvedValue(true)
  })

  it('searches users by visible identity instead of requiring an ID', async () => {
    const wrapper = mountPage(pinia)
    await flushPromises()

    expect(wrapper.text()).toContain('Nguyễn Văn Target')
    expect(wrapper.text()).toContain('target@example.com')

    await wrapper.get('#role-user-search').setValue('Target')
    await wrapper.get('form[role="search"]').trigger('submit')
    await flushPromises()

    expect(authApi.roleUsers).toHaveBeenLastCalledWith({
      search: 'Target',
      role: undefined,
      is_active: undefined,
      page: 1,
      page_size: 20,
    })
  })

  it('combines role and account-status filters', async () => {
    const wrapper = mountPage(pinia)
    await flushPromises()

    await wrapper.get('#role-filter').setValue('seller')
    await wrapper.get('#status-filter').setValue('locked')
    await wrapper.get('form[role="search"]').trigger('submit')
    await flushPromises()

    expect(authApi.roleUsers).toHaveBeenLastCalledWith({
      search: undefined,
      role: 'seller',
      is_active: false,
      page: 1,
      page_size: 20,
    })
  })

  it('defaults the assignment dropdown to the selected current role', async () => {
    vi.mocked(authApi.roleUsers).mockResolvedValue(listResponse([adminUser]))
    const wrapper = mountPage(pinia)
    await flushPromises()

    expect(wrapper.text()).toContain('admin-target')
    await wrapper.get('button[aria-label="Phân quyền cho admin-target"]').trigger('click')
    await flushPromises()

    expect((wrapper.get('#assigned-role').element as HTMLSelectElement).value).toBe('admin')
    expect(wrapper.get('aside button[type="submit"]').attributes('disabled')).toBeDefined()
  })

  it('requires confirmation before assigning a different role', async () => {
    vi.mocked(authApi.assignRole).mockResolvedValue({
      data: {
        success: true,
        message: 'Cập nhật vai trò thành công',
        data: { ...authenticatedUser(targetUser.id), role: 'seller' },
      },
    } as Awaited<ReturnType<typeof authApi.assignRole>>)
    const wrapper = mountPage(pinia)
    await flushPromises()

    await wrapper.get('button[aria-label="Phân quyền cho Nguyễn Văn Target"]').trigger('click')
    await flushPromises()
    await wrapper.get('#assigned-role').setValue('seller')
    await wrapper.get('aside form').trigger('submit')
    await flushPromises()

    expect(confirmDialog).toHaveBeenCalledWith(
      expect.objectContaining({ confirmLabel: 'Xác nhận đổi vai trò' }),
    )
    expect(authApi.assignRole).toHaveBeenCalledWith(17, 'seller')
    expect(analyticsApi.auditLogs).toHaveBeenCalledWith({
      action: 'assign_role',
      target_type: 'User',
      target_id: '17',
    })
  })

  it('identifies and prevents role changes to the signed-in account', async () => {
    useAuthStore().$patch({ user: authenticatedUser(targetUser.id) })
    const wrapper = mountPage(pinia)
    await flushPromises()

    expect(wrapper.text()).toContain('Đây là tài khoản của bạn')
    await wrapper.get('button[aria-label="Phân quyền cho Nguyễn Văn Target"]').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('bạn không thể tự thay đổi vai trò')
    expect(wrapper.get('#assigned-role').attributes('disabled')).toBeDefined()
    expect(wrapper.get('aside button[type="submit"]').attributes('disabled')).toBeDefined()
  })

  it('loads another page and reports the total number of users', async () => {
    vi.mocked(authApi.roleUsers)
      .mockResolvedValueOnce(listResponse([targetUser], 1, 2))
      .mockResolvedValueOnce(listResponse([adminUser], 2, 2))
    const wrapper = mountPage(pinia)
    await flushPromises()

    expect(wrapper.text()).toContain('25 người dùng')
    await wrapper.get('nav[aria-label="Phân trang người dùng"] button:last-child').trigger('click')
    await flushPromises()

    expect(authApi.roleUsers).toHaveBeenLastCalledWith(
      expect.objectContaining({ page: 2, page_size: 20 }),
    )
  })
})
