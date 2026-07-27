import { AxiosError, type AxiosResponse } from 'axios'
import { describe, expect, it } from 'vitest'

import { getErrorMessage } from './errors'

describe('getErrorMessage', () => {
  it('shows field-level API validation errors instead of a generic 400 message', () => {
    const response = {
      data: {
        success: false,
        message: 'Dữ liệu không hợp lệ',
        errors: {
          password: ['Mật khẩu này quá phổ biến.', 'Mật khẩu này hoàn toàn là số.'],
          date_of_birth: ['Ngày sai định dạng.'],
        },
      },
      status: 400,
      statusText: 'Bad Request',
      headers: {},
      config: { headers: {} },
    } as AxiosResponse
    const error = new AxiosError(
      'Request failed',
      'ERR_BAD_REQUEST',
      undefined,
      undefined,
      response,
    )

    expect(getErrorMessage(error)).toBe(
      'Mật khẩu: Mật khẩu này quá phổ biến. · Mật khẩu: Mật khẩu này hoàn toàn là số. · Ngày sinh: Ngày sai định dạng.',
    )
  })
})
