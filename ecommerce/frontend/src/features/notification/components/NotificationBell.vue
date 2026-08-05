<script setup lang="ts">
import { BellIcon } from '@heroicons/vue/24/outline'
import { onMounted } from 'vue'

import { useAuthStore } from '@/stores/auth'

import { useNotifications } from '../composables/useNotifications'

defineProps<{ to: string }>()

const authStore = useAuthStore()
const center = useNotifications(() => authStore.accessToken)
const { unreadCount } = center

onMounted(() => {
  if (authStore.accessToken && import.meta.env.MODE !== 'test') {
    void center.start().catch(() => undefined)
  }
})
</script>

<template>
  <RouterLink
    class="relative grid h-10 w-10 place-items-center rounded-xl text-slate-600 hover:bg-indigo-50 hover:text-indigo-700"
    :to="to"
    aria-label="Trung tâm thông báo"
  >
    <BellIcon class="h-5 w-5" />
    <span
      v-if="center.unreadCount"
      class="absolute -right-1 -top-1 min-w-5 rounded-full bg-rose-600 px-1 text-center text-[10px] font-black leading-5 text-white"
    >
      {{ unreadCount > 99 ? '99+' : unreadCount }}
    </span>
  </RouterLink>
</template>
