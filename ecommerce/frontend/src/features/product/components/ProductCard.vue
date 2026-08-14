<script setup lang="ts">
import { CheckIcon, ScaleIcon, StarIcon } from '@heroicons/vue/24/outline'
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
const hasDiscount = computed(
  () =>
    Boolean(props.product.is_flash_sale && props.product.regular_min_price) &&
    Number(props.product.regular_min_price) > Number(props.product.min_price),
)
const hasPriceRange = computed(
  () =>
    Boolean(props.product.max_price) &&
    Number(props.product.max_price) > Number(props.product.min_price),
)
</script>

<template>
  <article
    class="group relative flex h-full flex-col overflow-hidden rounded-2xl bg-[#fffdf8] shadow-[0_10px_30px_rgba(23,59,53,0.08)]"
  >
    <div
      class="absolute left-3 top-3 z-10"
      data-test="compare-control"
      :title="compareDisabled ? 'Tối đa 4 sản phẩm' : undefined"
    >
      <button
        class="grid h-11 w-11 place-items-center rounded-xl bg-[#fffdf8]/95 text-[#173b35] shadow-md transition hover:bg-[#f2c14e] disabled:cursor-not-allowed disabled:opacity-50"
        :class="
          selectedForCompare ? 'bg-[#f2c14e] text-[#173b35]' : 'bg-[#fffdf8]/95 text-[#173b35]'
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
        <CheckIcon v-if="selectedForCompare" class="h-5 w-5" />
        <ScaleIcon v-else class="h-5 w-5" />
        <span class="sr-only">{{ selectedForCompare ? 'Đã chọn' : 'Thêm vào so sánh' }}</span>
      </button>
    </div>
    <RouterLink
      :to="{
        name: 'product-detail',
        params: { slug: product.slug },
        query: { shop: product.shop_slug },
      }"
      class="flex flex-1 flex-col focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#e85d3f]"
    >
      <div class="relative aspect-[4/3] overflow-hidden bg-[#ece8de]">
        <img
          v-if="product.thumbnail && !imageFailed"
          :src="product.thumbnail"
          :alt="product.name"
          class="h-full w-full object-cover transition duration-500 ease-out group-hover:scale-[1.03]"
          loading="lazy"
          decoding="async"
          @error="imageFailed = true"
        />
        <div
          v-else
          class="grid h-full place-items-center bg-[#e8eee9] text-[#526762]"
          role="img"
          :aria-label="`Chưa có ảnh cho ${product.name}`"
        >
          <div class="text-center">
            <span
              class="mx-auto grid size-14 place-items-center rounded-xl bg-[#fffdf8] font-black text-[#173b35] shadow-sm"
              >M</span
            ><span class="mt-2 block text-xs font-semibold">Ảnh đang cập nhật</span>
          </div>
        </div>
        <span
          class="absolute bottom-3 left-3 rounded-lg bg-[#fffdf8]/95 px-2.5 py-1 text-xs font-bold text-[#526762] shadow-sm"
        >
          {{ product.sold_count }} đã bán
        </span>
        <span
          v-if="product.is_flash_sale"
          class="absolute bottom-3 right-3 rounded-lg bg-[#e85d3f] px-2.5 py-1 text-xs font-black text-white shadow-sm"
        >
          FLASH SALE
        </span>
      </div>
      <div class="flex flex-1 flex-col p-4">
        <p class="text-xs font-bold text-[#526762]">
          {{ product.shop_name }}
        </p>
        <h2 class="mt-1.5 line-clamp-2 text-base font-bold leading-6 text-[#0b2a25]">
          {{ product.name }}
        </h2>
        <div class="mt-2.5 flex items-center gap-1 text-sm text-[#526762]">
          <StarIcon class="h-4 w-4 fill-[#f2c14e] text-[#f2c14e]" aria-hidden="true" />
          <strong class="text-[#173b35]">{{ Number(product.rating_average).toFixed(1) }}</strong>
          <span>({{ product.rating_count }})</span>
        </div>
        <div class="mt-auto pt-4">
          <p class="text-xl font-black tracking-tight text-[#e85d3f]">
            {{ formatVnd(product.min_price) }}
          </p>
          <p v-if="hasDiscount" class="mt-0.5 text-sm text-[#71827e] line-through">
            {{ formatVnd(product.regular_min_price) }}
          </p>
          <p v-if="hasPriceRange" class="mt-0.5 text-xs text-[#526762]">
            Giá từ {{ formatVnd(product.min_price) }} đến {{ formatVnd(product.max_price) }}
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
