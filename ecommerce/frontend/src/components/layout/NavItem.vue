<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import type { NavItem } from '@/config/nav.config'

const props = defineProps<{ item: NavItem }>()
const route = useRoute()

const isActive = computed(() => {
  if (props.item.exact) {
    return route.path === props.item.to
  }
  return route.path.startsWith(props.item.to)
})
</script>

<template>
  <RouterLink
    :to="item.to"
    :class="[
      isActive
        ? 'bg-indigo-500 text-white'
        : 'text-slate-300 hover:bg-white/10 hover:text-white',
      'group flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-bold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500'
    ]"
    :aria-current="isActive ? 'page' : undefined"
  >
    <component
      :is="item.icon"
      :class="[
        isActive ? 'text-white' : 'text-slate-400 group-hover:text-white',
        'h-5 w-5 shrink-0 transition-colors'
      ]"
      aria-hidden="true"
    />
    {{ item.label }}
  </RouterLink>
</template>
