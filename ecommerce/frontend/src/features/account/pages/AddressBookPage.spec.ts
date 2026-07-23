import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { accountApi } from '../api'
import AddressBookPage from './AddressBookPage.vue'

vi.mock('../api', () => ({
  accountApi: {
    listAddresses: vi.fn(),
    createAddress: vi.fn(),
    updateAddress: vi.fn(),
    deleteAddress: vi.fn(),
    setDefaultAddress: vi.fn(),
  },
}))

const address = {
  id: 1,
  recipient_name: 'Nguyễn Văn A',
  phone: '0901234567',
  province: 'Hà Nội',
  district: 'Cầu Giấy',
  ward: 'Dịch Vọng',
  detail_address: 'Số 1 đường Test',
  is_default: false,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

describe('AddressBookPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(accountApi.listAddresses).mockResolvedValue({
      data: { success: true, message: 'ok', data: [address] },
    } as Awaited<ReturnType<typeof accountApi.listAddresses>>)
    vi.mocked(accountApi.setDefaultAddress).mockResolvedValue({
      data: {
        success: true,
        message: 'Đã đặt địa chỉ mặc định',
        data: { ...address, is_default: true },
      },
    } as Awaited<ReturnType<typeof accountApi.setDefaultAddress>>)
  })

  it('loads addresses and lets the owner choose the default address', async () => {
    const wrapper = mount(AddressBookPage, {
      global: { stubs: { RouterLink: RouterLinkStub } },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('Nguyễn Văn A')
    expect(wrapper.text()).toContain('Số 1 đường Test')

    const defaultButton = wrapper
      .findAll('button')
      .find((button) => button.text() === 'Đặt mặc định')
    await defaultButton?.trigger('click')
    await flushPromises()

    expect(accountApi.setDefaultAddress).toHaveBeenCalledWith(1)
    expect(accountApi.listAddresses).toHaveBeenCalledTimes(2)
  })

  it('uses cascading province, district and ward selects', async () => {
    const wrapper = mount(AddressBookPage, {
      global: { stubs: { RouterLink: RouterLinkStub } },
    })
    await flushPromises()
    const [province, district, ward] = wrapper.findAll('select')

    expect(district.attributes('disabled')).toBeDefined()
    expect(ward.attributes('disabled')).toBeDefined()

    await province.setValue('Hà Nội')
    expect(district.attributes('disabled')).toBeUndefined()
    expect(district.text()).toContain('Cầu Giấy')

    await district.setValue('Cầu Giấy')
    expect(ward.attributes('disabled')).toBeUndefined()
    expect(ward.text()).toContain('Dịch Vọng')

    await province.setValue('Đà Nẵng')
    expect(district.element.value).toBe('')
    expect(ward.element.value).toBe('')
  })
})
