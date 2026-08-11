import { reactive, readonly } from 'vue'

export interface ConfirmDialogOptions {
  title: string
  message?: string
  confirmLabel?: string
  cancelLabel?: string
  destructive?: boolean
}

export interface PromptDialogOptions extends ConfirmDialogOptions {
  inputLabel: string
  initialValue?: string
  placeholder?: string
  required?: boolean
}

type DialogMode = 'confirm' | 'prompt'
type DialogResult = boolean | string | null

const state = reactive({
  open: false,
  mode: 'confirm' as DialogMode,
  title: '',
  message: '',
  confirmLabel: 'Xác nhận',
  cancelLabel: 'Hủy',
  destructive: false,
  inputLabel: '',
  initialValue: '',
  placeholder: '',
  required: false,
})

let resolveCurrent: ((result: DialogResult) => void) | null = null

function closeWith(result: DialogResult): void {
  state.open = false
  const resolve = resolveCurrent
  resolveCurrent = null
  resolve?.(result)
}

function cancelPendingDialog(): void {
  if (!resolveCurrent) return
  closeWith(state.mode === 'confirm' ? false : null)
}

function openDialog(mode: DialogMode, options: ConfirmDialogOptions | PromptDialogOptions): void {
  cancelPendingDialog()
  Object.assign(state, {
    open: true,
    mode,
    title: options.title,
    message: options.message ?? '',
    confirmLabel: options.confirmLabel ?? 'Xác nhận',
    cancelLabel: options.cancelLabel ?? 'Hủy',
    destructive: options.destructive ?? false,
    inputLabel: mode === 'prompt' ? (options as PromptDialogOptions).inputLabel : '',
    initialValue: mode === 'prompt' ? ((options as PromptDialogOptions).initialValue ?? '') : '',
    placeholder: mode === 'prompt' ? ((options as PromptDialogOptions).placeholder ?? '') : '',
    required: mode === 'prompt' ? ((options as PromptDialogOptions).required ?? false) : false,
  })
}

export function confirmDialog(options: ConfirmDialogOptions): Promise<boolean> {
  openDialog('confirm', options)
  return new Promise<boolean>((resolve) => {
    resolveCurrent = resolve as (result: DialogResult) => void
  })
}

export function promptDialog(options: PromptDialogOptions): Promise<string | null> {
  openDialog('prompt', options)
  return new Promise<string | null>((resolve) => {
    resolveCurrent = resolve as (result: DialogResult) => void
  })
}

export function useAppDialogHost() {
  return {
    state: readonly(state),
    confirm: () => closeWith(true),
    submitPrompt: (value: string) => closeWith(value),
    cancel: () => closeWith(state.mode === 'confirm' ? false : null),
  }
}
