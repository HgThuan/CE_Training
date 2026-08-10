import { ref } from 'vue'

export interface CartToastItem {
  product_name: string
  variant_name?: string
  quantity: number
  price: string
  image?: string | null
}

export interface CartToastData {
  status: 'success' | 'error'
  message?: string
  item?: CartToastItem
}

const showToast = ref(false)
const toastData = ref<CartToastData | null>(null)
let timeoutId: number | null = null

export function useCartToast() {
  function show(data: CartToastData) {
    if (timeoutId) {
      window.clearTimeout(timeoutId)
    }
    toastData.value = data
    showToast.value = true
    
    // Auto-close after 5 seconds
    timeoutId = window.setTimeout(() => {
      showToast.value = false
    }, 5000)
  }
  
  function hide() {
    if (timeoutId) {
      window.clearTimeout(timeoutId)
      timeoutId = null
    }
    showToast.value = false
  }

  return {
    showToast,
    toastData,
    show,
    hide,
  }
}
