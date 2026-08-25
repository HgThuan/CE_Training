<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, useId, watch } from 'vue'

import type { PublicProductListItem } from '../types'
import {
  trackRecommendationClick,
  trackRecommendationImpression,
  type RecommendationSource,
} from '../recommendationTracking'
import ProductCard from './ProductCard.vue'

const props = withDefaults(
  defineProps<{
    title: string
    products: PublicProductListItem[]
    loading?: boolean
    recommendationId?: string
    source?: RecommendationSource
  }>(),
  {
    loading: false,
    recommendationId: '',
    source: 'product',
  },
)

const headingId = `product-recommendations-${useId()}`
const listElement = ref<HTMLElement | null>(null)
const recordedImpressions = new Set<string>()
let impressionObserver: IntersectionObserver | null = null
let observerGeneration = 0

function recordVisibleProduct(element: HTMLElement): void {
  const productId = element.dataset.recommendationProductId
  const position = Number(element.dataset.recommendationPosition)
  const recommendationId = props.recommendationId
  if (!recommendationId || !productId || !Number.isInteger(position)) return

  const key = `${recommendationId}:${productId}:${props.source}`
  if (recordedImpressions.has(key)) return
  recordedImpressions.add(key)
  impressionObserver?.unobserve(element)
  trackRecommendationImpression(recommendationId, productId, props.source, position)
}

function recordProductsVisibleWithoutObserver(elements: HTMLElement[]): void {
  const rootBounds = listElement.value?.getBoundingClientRect()
  if (!rootBounds?.width || !rootBounds.height) return

  elements.forEach((element) => {
    const bounds = element.getBoundingClientRect()
    const visibleWidth = Math.max(
      0,
      Math.min(bounds.right, rootBounds.right) - Math.max(bounds.left, rootBounds.left),
    )
    const verticallyVisible = bounds.bottom > rootBounds.top && bounds.top < rootBounds.bottom
    if (verticallyVisible && bounds.width > 0 && visibleWidth / bounds.width >= 0.5) {
      recordVisibleProduct(element)
    }
  })
}

async function observeProductImpressions(): Promise<void> {
  const generation = ++observerGeneration
  impressionObserver?.disconnect()
  impressionObserver = null
  await nextTick()
  if (generation !== observerGeneration || props.loading || !props.recommendationId) return

  const root = listElement.value
  if (!root) return
  const elements = Array.from(
    root.querySelectorAll<HTMLElement>('[data-recommendation-product-id]'),
  )
  if (typeof IntersectionObserver === 'undefined') {
    recordProductsVisibleWithoutObserver(elements)
    return
  }

  impressionObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting && entry.intersectionRatio >= 0.5) {
          recordVisibleProduct(entry.target as HTMLElement)
        }
      })
    },
    { root, threshold: 0.5 },
  )
  elements.forEach((element) => impressionObserver?.observe(element))
}

watch(
  () =>
    [
      props.recommendationId,
      props.source,
      props.loading ? 'loading' : 'ready',
      props.products.map((product) => product.id).join(','),
    ].join('|'),
  () => void observeProductImpressions(),
  { immediate: true, flush: 'post' },
)

onBeforeUnmount(() => {
  observerGeneration += 1
  impressionObserver?.disconnect()
})
</script>

<template>
  <section v-if="loading || products.length" :aria-labelledby="headingId" :aria-busy="loading">
    <h2 :id="headingId" class="text-2xl font-black tracking-tight text-slate-950 sm:text-3xl">
      {{ title }}
    </h2>

    <p v-if="loading" class="sr-only" role="status">Đang tải {{ title.toLowerCase() }}</p>
    <ul
      ref="listElement"
      class="mt-6 flex snap-x snap-mandatory gap-5 overflow-x-auto pb-5"
      :aria-label="title"
    >
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
        v-for="(product, index) in loading ? [] : products"
        :key="product.id"
        :data-recommendation-product-id="product.id"
        :data-recommendation-position="index"
        class="w-[78vw] max-w-[19rem] shrink-0 snap-start sm:w-72 lg:w-[calc(25%-0.9375rem)]"
      >
        <ProductCard
          :product="product"
          @click.capture="trackRecommendationClick(recommendationId, product.id, source, index)"
        />
      </li>
    </ul>
  </section>
</template>
