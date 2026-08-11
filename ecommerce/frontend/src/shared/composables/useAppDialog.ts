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
  inputType?: 'text' | 'number' | 'url'
}

type DialogMode = 'alert' | 'confirm' | 'prompt'
type DialogResult = boolean | string | null | undefined

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
  inputType: 'text' as 'text' | 'number' | 'url',
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
  closeWith(state.mode === 'prompt' ? null : state.mode === 'confirm' ? false : undefined)
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
    inputType: mode === 'prompt' ? ((options as PromptDialogOptions).inputType ?? 'text') : 'text',
  })
}

export function alertDialog(options: ConfirmDialogOptions): Promise<void> {
  openDialog('alert', { ...options, confirmLabel: options.confirmLabel ?? 'Đóng' })
  return new Promise<void>((resolve) => {
    resolveCurrent = resolve as (result: DialogResult) => void
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
    confirm: () => closeWith(state.mode === 'alert' ? undefined : true),
    submitPrompt: (value: string) => closeWith(value),
    cancel: () =>
      closeWith(state.mode === 'prompt' ? null : state.mode === 'confirm' ? false : undefined),
  }
}
