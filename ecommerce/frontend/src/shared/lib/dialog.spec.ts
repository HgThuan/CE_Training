import { showAlert, showConfirm, showPrompt } from './dialog'

describe('custom dialogs', () => {
  afterEach(() => {
    document.body.innerHTML = ''
    document.body.style.overflow = ''
  })

  it('collects a required prompt value without using the browser prompt', async () => {
    const result = showPrompt('Nhập lý do', { required: true })
    const input = document.querySelector<HTMLInputElement>('input')
    const confirm = Array.from(document.querySelectorAll('button')).find(
      (element) => element.textContent === 'Xác nhận',
    )

    expect(input).not.toBeNull()
    input!.value = 'Khách yêu cầu'
    confirm!.click()

    await expect(result).resolves.toBe('Khách yêu cầu')
    expect(document.querySelector('[role="dialog"]')).toBeNull()
  })

  it('returns false when a confirmation is cancelled', async () => {
    const result = showConfirm('Xóa dữ liệu?')
    const cancel = Array.from(document.querySelectorAll('button')).find(
      (element) => element.textContent === 'Hủy',
    )
    cancel!.click()

    await expect(result).resolves.toBe(false)
  })

  it('renders and closes an application alert', async () => {
    const result = showAlert('Đã hoàn tất')
    const confirm = document.querySelector<HTMLButtonElement>('button')
    expect(document.body.textContent).toContain('Đã hoàn tất')
    confirm!.click()

    await expect(result).resolves.toBeUndefined()
  })
})
