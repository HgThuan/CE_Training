<script setup lang="ts">
import { useId } from 'vue'

import type { PublicProductListItem } from '../types'
import ProductCard from './ProductCard.vue'

withDefaults(
  defineProps<{
    title: string
    products: PublicProductListItem[]
    loading?: boolean
  }>(),
  {
    loading: false,
  },
)

const headingId = `product-recommendations-${useId()}`
</script>

<template>
  <section v-if="loading || products.length" :aria-labelledby="headingId" :aria-busy="loading">
    <h2 :id="headingId" class="text-2xl font-black tracking-tight text-slate-950 sm:text-3xl">
      {{ title }}
    </h2>

    <p v-if="loading" class="sr-only" role="status">Đang tải {{ title.toLowerCase() }}</p>
    <ul class="mt-6 flex snap-x snap-mandatory gap-5 overflow-x-auto pb-5" :aria-label="title">
      <template v-if="loading">
        <li
          v-for="index in 4"
          :key="index"
          class="w-[78vw] max-w-[19rem] shrink-0 snap-start sm:w-72 lg:w-[calc(25%-0.9375rem)]"
          aria-hidden="true"
        >
          <div class="overflow-hidden rounded-3xl bg-white ring-1 ring-slate-200">
            <div class="aspect-[4/3] animate-pulse bg-slate-200" />
            <div class="space-y-3 p-5">
              <div class="h-3 w-1/3 animate-pulse rounded bg-slate-200" />
              <div class="h-5 animate-pulse rounded bg-slate-200" />
              <div class="h-5 w-2/3 animate-pulse rounded bg-slate-200" />
            </div>
          </div>
        </li>
      </template>
      <li
        v-for="product in loading ? [] : products"
        :key="product.id"
        class="w-[78vw] max-w-[19rem] shrink-0 snap-start sm:w-72 lg:w-[calc(25%-0.9375rem)]"
      >
        <ProductCard :product="product" />
      </li>
    </ul>
  </section>
</template>
