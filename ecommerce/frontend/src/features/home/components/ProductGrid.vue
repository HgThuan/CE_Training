<script setup lang="ts">
import { ShoppingBagIcon } from '@heroicons/vue/24/outline'

import ProductCard from '@/features/product/components/ProductCard.vue'
import type { PublicProductListItem } from '@/features/product/types'

withDefaults(
  defineProps<{
    title: string
    description?: string
    products: PublicProductListItem[]
    emptyMessage?: string
  }>(),
  {
    description: '',
    emptyMessage: 'Chưa có sản phẩm trong mục này.',
  },
)
</script>

<template>
  <section>
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <h2 class="text-2xl font-black tracking-tight text-slate-950 sm:text-3xl">{{ title }}</h2>
        <p v-if="description" class="mt-2 text-slate-600">{{ description }}</p>
      </div>
      <RouterLink class="text-sm font-bold text-indigo-700 hover:text-indigo-900" to="/products">
        Xem tất cả →
      </RouterLink>
    </div>

    <div
      v-if="products.length"
      class="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
    >
      <ProductCard v-for="product in products" :key="product.id" :product="product" />
    </div>

    <div
      v-else
      class="mt-6 rounded-3xl border border-dashed border-slate-300 bg-white px-6 py-12 text-center"
    >
      <ShoppingBagIcon class="mx-auto h-10 w-10 text-slate-400" />
      <p class="mt-3 text-sm font-semibold text-slate-600">{{ emptyMessage }}</p>
    </div>
  </section>
</template>
