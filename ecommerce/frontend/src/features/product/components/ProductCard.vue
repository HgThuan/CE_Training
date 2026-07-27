<script setup lang="ts">
import { PhotoIcon, StarIcon } from '@heroicons/vue/24/outline'
import { ref } from 'vue'

import { formatVnd } from '@/shared/lib/formatters'

import type { PublicProductListItem } from '../types'

defineProps<{ product: PublicProductListItem }>()

const imageFailed = ref(false)
</script>

<template>
  <RouterLink
    :to="{
      name: 'product-detail',
      params: { slug: product.slug },
      query: { shop: product.shop_slug },
    }"
    class="group flex h-full flex-col overflow-hidden rounded-3xl bg-white shadow-sm ring-1 ring-slate-200 transition duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-slate-200/70 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-indigo-600"
  >
    <div class="relative aspect-[4/3] overflow-hidden bg-slate-100">
      <img
        v-if="product.thumbnail && !imageFailed"
        :src="product.thumbnail"
        :alt="product.name"
        class="h-full w-full object-cover transition duration-500 group-hover:scale-105"
        loading="lazy"
        @error="imageFailed = true"
      />
      <div v-else class="grid h-full place-items-center text-slate-400">
        <PhotoIcon class="h-12 w-12" aria-hidden="true" />
      </div>
      <span
        class="absolute left-4 top-4 rounded-full bg-white/90 px-3 py-1 text-xs font-bold text-slate-700 shadow-sm backdrop-blur"
      >
        {{ product.sold_count }} đã bán
      </span>
    </div>
    <div class="flex flex-1 flex-col p-5">
      <p class="text-xs font-semibold uppercase tracking-wider text-indigo-600">
        {{ product.shop_name }}
      </p>
      <h2 class="mt-2 line-clamp-2 text-lg font-bold leading-6 text-slate-950">
        {{ product.name }}
      </h2>
      <div class="mt-3 flex items-center gap-1 text-sm text-slate-600">
        <StarIcon class="h-4 w-4 fill-amber-400 text-amber-400" aria-hidden="true" />
        <strong class="text-slate-900">{{ Number(product.rating_average).toFixed(1) }}</strong>
        <span>({{ product.rating_count }})</span>
      </div>
      <div class="mt-auto pt-5">
        <p class="text-xl font-black tracking-tight text-indigo-700">
          {{ formatVnd(product.min_price) }}
        </p>
        <p
          v-if="product.max_price && product.max_price !== product.min_price"
          class="mt-0.5 text-xs text-slate-500"
        >
          đến {{ formatVnd(product.max_price) }}
        </p>
      </div>
    </div>
  </RouterLink>
</template>
