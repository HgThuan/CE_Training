import { AxiosError, type AxiosResponse } from 'axios'
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import VoucherForm from './VoucherForm.vue'

describe('VoucherForm', () => {
  it('blocks submit when discount value and dates are invalid', async () => {
    const wrapper = mount(VoucherForm, { props: { scope: 'platform' } })
    const numbers = wrapper.findAll('input[type="number"]')
    await numbers[0]?.setValue(0)
    const dates = wrapper.findAll('input[type="datetime-local"]')
    await dates[1]?.setValue('2020-01-01T00:00')
    await wrapper.find('form').trigger('submit')

    expect(wrapper.emitted('submit')).toBeUndefined()
    expect(wrapper.text()).toContain('Giá trị giảm phải lớn hơn 0')
    expect(wrapper.text()).toContain('Thời điểm kết thúc phải sau thời điểm bắt đầu')
  })

  it('shows the backend response message and field error', async () => {
    const wrapper = mount(VoucherForm, { props: { scope: 'shop' } })
    const response = {
      status: 400,
      statusText: 'Bad Request',
      headers: {},
      config: { headers: {} },
      data: {
        message: 'Dữ liệu không hợp lệ',
        errors: { code: ['Mã voucher đã tồn tại'] },
      },
    } as AxiosResponse
    const error = new AxiosError('bad request', 'ERR_BAD_REQUEST', undefined, undefined, response)
    ;(wrapper.vm as unknown as { showServerError: (value: unknown) => void }).showServerError(error)
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Dữ liệu không hợp lệ')
    expect(wrapper.text()).toContain('Mã voucher đã tồn tại')
  })
})
