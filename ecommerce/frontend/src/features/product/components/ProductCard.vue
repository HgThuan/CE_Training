<script setup lang="ts">
import { CheckIcon, PhotoIcon, ScaleIcon, StarIcon } from '@heroicons/vue/24/outline'
import { computed, ref } from 'vue'

import { formatVnd } from '@/shared/lib/formatters'
import WishlistToggleButton from '@/features/wishlist/components/WishlistToggleButton.vue'

import type { PublicProductListItem } from '../types'
import { useCompareStore } from '../compare-store'

const props = defineProps<{ product: PublicProductListItem }>()

const imageFailed = ref(false)
const compareStore = useCompareStore()
const selectedForCompare = computed(() => compareStore.isSelected(props.product.id))
const compareDisabled = computed(() => compareStore.isFull && !selectedForCompare.value)
</script>

<template>
  <article class="relative flex h-full flex-col gap-2">
    <div data-test="compare-control" :title="compareDisabled ? 'Tối đa 4 sản phẩm' : undefined">
      <button
        class="flex w-full items-center justify-center gap-2 rounded-xl border px-3 py-2 text-sm font-bold transition disabled:cursor-not-allowed disabled:opacity-50"
        :class="
          selectedForCompare
            ? 'border-indigo-600 bg-indigo-50 text-indigo-700'
            : 'border-slate-300 bg-white text-slate-700 hover:border-indigo-400 hover:text-indigo-700'
        "
        type="button"
        :disabled="compareDisabled"
        :aria-pressed="selectedForCompare"
        :aria-label="
          selectedForCompare
            ? `Bỏ ${product.name} khỏi danh sách so sánh`
            : `Thêm ${product.name} vào danh sách so sánh`
        "
        @click="compareStore.toggle(product)"
      >
        <CheckIcon v-if="selectedForCompare" class="h-4 w-4" />
        <ScaleIcon v-else class="h-4 w-4" />
        {{ selectedForCompare ? 'Đã chọn ✓' : 'Thêm vào so sánh' }}
      </button>
    </div>
    <RouterLink
      :to="{
        name: 'product-detail',
        params: { slug: product.slug },
        query: { shop: product.shop_slug },
      }"
      class="group flex flex-1 flex-col overflow-hidden rounded-3xl bg-white shadow-sm ring-1 ring-slate-200 transition duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-slate-200/70 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-indigo-600"
    >
      <div class="relative aspect-[4/3] overflow-hidden bg-slate-100">
        <img
          v-if="product.thumbnail && !imageFailed"
          :src="product.thumbnail"
          :alt="product.name"
          class="h-full w-full object-cover transition duration-500 group-hover:scale-105"
          loading="lazy"
          decoding="async"
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
        <span
          v-if="product.is_flash_sale"
          class="absolute right-4 top-4 rounded-full bg-rose-600 px-3 py-1 text-xs font-black text-white shadow-sm"
        >
          FLASH SALE
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
            v-if="product.is_flash_sale && product.regular_min_price"
            class="mt-0.5 text-sm text-slate-400 line-through"
          >
            {{ formatVnd(product.regular_min_price) }}
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
    <WishlistToggleButton
      class="absolute right-3 top-3 z-10"
      :product-id="product.id"
      :product-name="product.name"
      variant="overlay"
    />
  </article>
</template>
