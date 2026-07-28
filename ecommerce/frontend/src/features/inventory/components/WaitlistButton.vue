<script setup lang="ts">
import { BellAlertIcon } from '@heroicons/vue/24/outline'

import { useWaitlist } from '../composables/useWaitlist'

defineProps<{ variantId: string }>()

const { joining, message, errorMessage, join } = useWaitlist()
</script>

<template>
  <div class="mt-4">
    <button
      class="inline-flex items-center gap-2 rounded-xl bg-amber-100 px-4 py-2.5 text-sm font-bold text-amber-900 hover:bg-amber-200 disabled:opacity-50"
      type="button"
      :disabled="joining || Boolean(message)"
      @click="join(variantId)"
    >
      <BellAlertIcon class="h-5 w-5" />
      {{ joining ? 'Đang đăng ký…' : message || 'Báo tôi khi có hàng' }}
    </button>
    <p v-if="errorMessage" class="mt-2 text-sm font-semibold text-rose-700" role="alert">
      {{ errorMessage }}
    </p>
  </div>
</template>
