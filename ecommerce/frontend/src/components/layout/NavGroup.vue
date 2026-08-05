<script setup lang="ts">
import type { NavGroup } from '@/config/nav.config'
import NavItem from './NavItem.vue'

defineProps<{ group: NavGroup }>()
</script>

<template>
  <div class="mb-6 last:mb-0">
    <div
      v-if="group.label"
      class="mb-2 px-3 text-xs font-bold uppercase tracking-wider text-slate-500"
    >
      {{ group.label }}
    </div>
    <ul role="list" class="flex flex-col gap-1">
      <li v-for="item in group.items" :key="item.to">
        <NavItem :item="item" />
      </li>
    </ul>
  </div>
</template>
