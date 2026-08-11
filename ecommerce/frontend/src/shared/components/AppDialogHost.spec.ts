import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import { nextTick } from 'vue'

import { alertDialog, confirmDialog, promptDialog } from '@/shared/composables/useAppDialog'

import AppDialogHost from './AppDialogHost.vue'

describe('AppDialogHost', () => {
  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('resolves a custom confirmation without using a browser dialog', async () => {
    const wrapper = mount(AppDialogHost, { attachTo: document.body })
    const result = confirmDialog({
      title: 'Xóa sản phẩm',
      message: 'Thao tác này không thể hoàn tác.',
      confirmLabel: 'Xóa',
      destructive: true,
    })
    await nextTick()

    const dialog = document.body.querySelector('[role="dialog"]')
    expect(dialog?.textContent).toContain('Xóa sản phẩm')
    const submit = dialog?.querySelector<HTMLButtonElement>('button[type="submit"]')
    submit?.click()

    await expect(result).resolves.toBe(true)
    wrapper.unmount()
  })

  it('collects required prompt input', async () => {
    const wrapper = mount(AppDialogHost, { attachTo: document.body })
    const result = promptDialog({
      title: 'Ẩn sản phẩm',
      inputLabel: 'Lý do',
      required: true,
    })
    await nextTick()

    const input = document.body.querySelector<HTMLInputElement>('input')
    expect(input).not.toBeNull()
    input!.value = 'Vi phạm chính sách'
    input!.dispatchEvent(new Event('input'))
    await nextTick()
    document.body.querySelector<HTMLButtonElement>('button[type="submit"]')?.click()

    await expect(result).resolves.toBe('Vi phạm chính sách')
    wrapper.unmount()
  })

  it('renders an application alert with a single close action', async () => {
    const wrapper = mount(AppDialogHost, { attachTo: document.body })
    const result = alertDialog({ title: 'Hoàn tất', message: 'Đã lưu thay đổi.' })
    await nextTick()

    const buttons = document.body.querySelectorAll<HTMLButtonElement>('button')
    expect(buttons).toHaveLength(1)
    expect(buttons[0]?.textContent).toContain('Đóng')
    buttons[0]?.click()

    await expect(result).resolves.toBeUndefined()
    wrapper.unmount()
  })
})
