export interface DialogOptions {
  title?: string
  confirmLabel?: string
  cancelLabel?: string
  initialValue?: string
  placeholder?: string
  inputType?: 'text' | 'number'
  multiline?: boolean
  required?: boolean
  tone?: 'default' | 'danger'
}

interface DialogConfig extends DialogOptions {
  message: string
  mode: 'alert' | 'confirm' | 'prompt'
}

function button(label: string, className: string): HTMLButtonElement {
  const element = document.createElement('button')
  element.type = 'button'
  element.textContent = label
  element.className = className
  return element
}

function openDialog(config: DialogConfig): Promise<string | boolean | null> {
  return new Promise((resolve) => {
    const previousFocus =
      document.activeElement instanceof HTMLElement ? document.activeElement : null
    const overlay = document.createElement('div')
    overlay.className =
      'fixed inset-0 z-[100] grid place-items-center bg-slate-950/60 p-4 backdrop-blur-sm'

    const panel = document.createElement('section')
    panel.className = 'w-full max-w-md rounded-3xl bg-white p-6 shadow-2xl'
    panel.setAttribute('role', 'dialog')
    panel.setAttribute('aria-modal', 'true')

    const title = document.createElement('h2')
    title.className = 'text-xl font-black text-slate-950'
    title.textContent =
      config.title ?? (config.mode === 'alert' ? 'Thông báo' : 'Xác nhận thao tác')
    panel.appendChild(title)

    const message = document.createElement('p')
    message.className = 'mt-2 whitespace-pre-line text-sm leading-6 text-slate-600'
    message.textContent = config.message
    panel.appendChild(message)

    let input: HTMLInputElement | HTMLTextAreaElement | null = null
    if (config.mode === 'prompt') {
      input = config.multiline
        ? document.createElement('textarea')
        : document.createElement('input')
      if (input instanceof HTMLInputElement) input.type = config.inputType ?? 'text'
      if (input instanceof HTMLTextAreaElement) input.rows = 4
      input.className =
        'mt-4 w-full rounded-xl border border-slate-300 px-3 py-2.5 text-slate-950 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100'
      input.value = config.initialValue ?? ''
      input.placeholder = config.placeholder ?? ''
      input.setAttribute('aria-label', config.title ?? config.message)
      panel.appendChild(input)
    }

    const validation = document.createElement('p')
    validation.className = 'mt-2 hidden text-sm font-semibold text-rose-700'
    validation.textContent = 'Vui lòng nhập nội dung trước khi tiếp tục.'
    panel.appendChild(validation)

    const actions = document.createElement('div')
    actions.className = 'mt-6 flex justify-end gap-3'
    const cancel = button(
      config.cancelLabel ?? 'Hủy',
      'rounded-xl border border-slate-300 px-4 py-2.5 font-bold text-slate-700 hover:bg-slate-50',
    )
    const confirm = button(
      config.confirmLabel ?? 'Xác nhận',
      config.tone === 'danger'
        ? 'rounded-xl bg-rose-600 px-4 py-2.5 font-bold text-white hover:bg-rose-700'
        : 'rounded-xl bg-indigo-600 px-4 py-2.5 font-bold text-white hover:bg-indigo-700',
    )
    if (config.mode !== 'alert') actions.appendChild(cancel)
    actions.appendChild(confirm)
    panel.appendChild(actions)
    overlay.appendChild(panel)

    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    document.body.appendChild(overlay)

    let settled = false
    const finish = (value: string | boolean | null): void => {
      if (settled) return
      settled = true
      document.removeEventListener('keydown', onKeydown)
      overlay.remove()
      document.body.style.overflow = previousOverflow
      previousFocus?.focus()
      resolve(value)
    }
    const submit = (): void => {
      if (config.mode === 'prompt') {
        const value = input?.value.trim() ?? ''
        if (config.required && !value) {
          validation.classList.remove('hidden')
          input?.focus()
          return
        }
        finish(value)
        return
      }
      finish(true)
    }
    const onKeydown = (event: KeyboardEvent): void => {
      if (event.key === 'Escape' && config.mode !== 'alert') finish(null)
      if (event.key === 'Enter' && !(input instanceof HTMLTextAreaElement)) submit()
    }

    cancel.addEventListener('click', () => finish(config.mode === 'confirm' ? false : null))
    confirm.addEventListener('click', submit)
    overlay.addEventListener('click', (event) => {
      if (event.target === overlay && config.mode !== 'alert') {
        finish(config.mode === 'confirm' ? false : null)
      }
    })
    document.addEventListener('keydown', onKeydown)
    queueMicrotask(() => (input ?? confirm).focus())
  })
}

export async function showConfirm(message: string, options: DialogOptions = {}): Promise<boolean> {
  return (await openDialog({ ...options, message, mode: 'confirm' })) === true
}

export async function showPrompt(
  message: string,
  options: DialogOptions = {},
): Promise<string | null> {
  const result = await openDialog({ ...options, message, mode: 'prompt' })
  return typeof result === 'string' ? result : null
}

export async function showAlert(message: string, options: DialogOptions = {}): Promise<void> {
  await openDialog({ ...options, message, mode: 'alert' })
}
