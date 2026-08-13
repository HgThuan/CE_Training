<script setup lang="ts">
import { BuildingStorefrontIcon } from '@heroicons/vue/24/outline'

import { formatVnd } from '@/shared/lib/formatters'

import type { CartItem, CartShopGroup } from '../types'
import CartItemRow from './CartItemRow.vue'

defineProps<{ group: CartShopGroup }>()
const emit = defineEmits<{
  update: [item: CartItem, payload: { quantity?: number; is_selected?: boolean }]
  remove: [item: CartItem]
}>()
</script>

<template>
  <section class="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
    <header class="flex items-center justify-between gap-3 bg-slate-50 px-5 py-4">
      <div class="flex items-center gap-3">
        <img
          v-if="group.logo_url"
          :src="group.logo_url"
          :alt="group.shop_name"
          class="h-9 w-9 rounded-xl object-cover"
        />
        <BuildingStorefrontIcon v-else class="h-7 w-7 text-indigo-600" />
        <RouterLink class="font-black hover:text-indigo-700" :to="`/shops/${group.shop_slug}`">
          {{ group.shop_name }}
        </RouterLink>
      </div>
      <p class="text-sm text-slate-500">
        Tạm tính: <strong class="text-slate-950">{{ formatVnd(group.subtotal) }}</strong>
      </p>
    </header>
    <CartItemRow
      v-for="item in group.items"
      :key="item.id"
      :item="item"
      @update="(target, payload) => emit('update', target, payload)"
      @remove="(target) => emit('remove', target)"
    />
  </section>
</template>
