import { ref } from 'vue'

import { getErrorMessage } from '@/features/auth/errors'

import { inventoryApi } from '../api'

export function useWaitlist() {
  const joining = ref(false)
  const message = ref('')
  const errorMessage = ref('')

  async function join(variantId: string): Promise<void> {
    joining.value = true
    message.value = ''
    errorMessage.value = ''
    try {
      const response = await inventoryApi.joinWaitlist(variantId)
      message.value = response.data.message
    } catch (error) {
      errorMessage.value = getErrorMessage(error)
    } finally {
      joining.value = false
    }
  }

  return { joining, message, errorMessage, join }
}

