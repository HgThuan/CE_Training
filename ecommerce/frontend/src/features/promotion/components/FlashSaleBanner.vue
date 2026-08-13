<script setup lang="ts">
import { computed } from 'vue'

import { useCartStore } from '@/features/cart/store'
import { formatVnd } from '@/shared/lib/formatters'

import { usePromotionStore } from '../store'
import FlashSaleCountdown from './FlashSaleCountdown.vue'

const props = withDefaults(defineProps<{ limit?: number }>(), { limit: 5 })
const store = usePromotionStore()
const cartStore = useCartStore()
const active = computed(() => store.flashSales.filter((sale) => sale.status === 'ongoing'))
const visibleItems = computed(() =>
  active.value.flatMap((sale) => sale.items).slice(0, props.limit),
)
const endTime = computed(() => active.value[0]?.end_time ?? '')

async function addItem(item: (typeof visibleItems.value)[number]): Promise<void> {
  await cartStore.addItem(item.variant, 1, {
    product_slug: item.product_slug ?? '',
    product_name: item.product_name ?? 'Sản phẩm Flash Sale',
    variant_name: item.variant_sku,
    image: item.primary_image,
    price: item.sale_price,
  })
}

void store.loadActiveFlashSales()
</script>

<template>
  <section
    v-if="visibleItems.length"
    class="my-8 rounded-[2rem] bg-gradient-to-r from-rose-700 to-orange-600 p-5 text-white shadow-xl sm:p-7"
  >
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <p class="text-xs font-black uppercase tracking-[0.24em] text-amber-200">Giờ vàng</p>
        <h2 class="text-2xl font-black">Flash Sale</h2>
      </div>
      <div class="rounded-2xl bg-black/25 px-4 py-2 text-sm">
        Kết thúc sau
        <FlashSaleCountdown
          v-if="endTime"
          class="ml-2"
          :end-time="endTime"
          @ended="store.loadActiveFlashSales"
        />
      </div>
    </header>
    <div class="mt-5 grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
      <article
        v-for="item in visibleItems"
        :key="item.id"
        class="rounded-2xl bg-white p-3 text-slate-900"
      >
        <img
          :src="item.primary_image || 'https://placehold.co/320x240?text=Flash+Sale'"
          :alt="item.product_name"
          class="aspect-square w-full rounded-xl object-cover"
        /><RouterLink
          class="mt-3 block line-clamp-2 text-sm font-bold hover:text-rose-700"
          :to="`/products/${item.product_slug}`"
          >{{ item.product_name }}</RouterLink
        >
        <p class="mt-2 text-lg font-black text-rose-600">{{ formatVnd(item.sale_price) }}</p>
        <p class="text-xs text-slate-400 line-through">{{ formatVnd(item.original_price) }}</p>
        <p class="mt-2 text-xs font-semibold text-slate-500">
          Đã bán {{ item.sold_count }}/{{ item.quota }}
        </p>
        <button
          class="mt-3 w-full rounded-xl bg-slate-950 px-3 py-2 text-xs font-bold text-white hover:bg-rose-700"
          @click="addItem(item)"
        >
          Thêm vào giỏ
        </button>
      </article>
    </div>
    <RouterLink class="mt-5 inline-block text-sm font-bold text-white underline" to="/flash-sales"
      >Xem tất cả Flash Sale</RouterLink
    >
  </section>
</template>
