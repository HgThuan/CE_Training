import { ref } from 'vue'

export interface CartToastItem {
  product_name: string
  variant_name?: string | null
  quantity: number
  price: string
  image?: string | null
}

export interface CartToastData {
  status: 'success' | 'error'
  message?: string
  item?: CartToastItem
}

const visible = ref(false)
const toastData = ref<CartToastData | null>(null)
let dismissTimeout: number | null = null

function clearDismissTimeout(): void {
  if (dismissTimeout === null) return
  window.clearTimeout(dismissTimeout)
  dismissTimeout = null
}

export function useCartToast() {
  function hide(): void {
    clearDismissTimeout()
    visible.value = false
  }

  function show(data: CartToastData): void {
    clearDismissTimeout()
    toastData.value = data
    visible.value = true
    dismissTimeout = window.setTimeout(() => {
      visible.value = false
      dismissTimeout = null
    }, 5000)
  }

  return { visible, toastData, show, hide }
}
