<script setup lang="ts">
import { computed, ref } from 'vue'

import { useCartStore } from '@/features/cart/store'
import { formatVnd } from '@/shared/lib/formatters'

import { flashSaleAvailableQuantity } from '../availability'
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
const addingVariantId = ref<string | null>(null)

async function addItem(item: (typeof visibleItems.value)[number]): Promise<void> {
  if (flashSaleAvailableQuantity(item) <= 0 || addingVariantId.value) return
  addingVariantId.value = item.variant
  try {
    await cartStore.addItem(item.variant, 1, {
      product_slug: item.product_slug ?? '',
      shop_slug: item.shop_slug,
      product_name: item.product_name ?? 'Sản phẩm Flash Sale',
      variant_name: item.variant_sku,
      image: item.primary_image,
      price: item.sale_price,
    })
  } catch {
    return
  } finally {
    addingVariantId.value = null
  }
}

void store.loadActiveFlashSales()
</script>

<template>
  <section
    class="market-flash-section market-receipt my-8 rounded-2xl p-5 text-[#0b2a25] shadow-[0_10px_30px_rgba(23,59,53,0.08)] sm:p-7"
  >
    <header class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="text-2xl font-black text-[#173b35]">Giờ vàng Flash Sale</h2>
      </div>
      <div v-if="visibleItems.length" class="flex items-center gap-3">
        <RouterLink class="text-sm font-bold text-[#c8452d] underline" to="/flash-sales">
          Xem tất cả
        </RouterLink>
        <div class="rounded-xl bg-[#f2c14e]/35 px-4 py-2 text-sm font-bold">
          Kết thúc sau
          <FlashSaleCountdown
            v-if="endTime"
            class="ml-2"
            :end-time="endTime"
            @ended="store.loadActiveFlashSales"
          />
        </div>
      </div>
    </header>
    <div
      v-if="!visibleItems.length"
      class="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-xl bg-[#f7f3ea] px-4 py-3 text-sm"
    >
      <p class="font-semibold text-[#526762]">Ưu đãi giờ vàng đang được cập nhật.</p>
      <RouterLink class="font-bold text-[#c8452d]" to="/flash-sales"
        >Xem lịch Flash Sale →</RouterLink
      >
    </div>
    <div
      v-if="visibleItems.length"
      class="market-flash-grid mt-5 grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5"
    >
      <article
        v-for="item in visibleItems"
        :key="item.id"
        class="market-flash-ticket rounded-xl bg-[#f7f3ea] p-3 text-[#0b2a25]"
      >
        <img
          :src="item.primary_image || 'https://placehold.co/320x240?text=Flash+Sale'"
          :alt="item.product_name"
          class="market-flash-ticket__image aspect-square w-full rounded-xl object-cover"
        /><RouterLink
          class="market-flash-ticket__name mt-3 block line-clamp-2 text-sm font-bold hover:text-rose-700"
          :to="{
            name: 'product-detail',
            params: { slug: item.product_slug },
            query: { shop: item.shop_slug },
          }"
          >{{ item.product_name }}</RouterLink
        >
        <p class="market-flash-ticket__price mt-2 text-lg font-black text-[#e85d3f]">
          {{ formatVnd(item.sale_price) }}
        </p>
        <p
          v-if="Number(item.original_price) > Number(item.sale_price)"
          class="market-flash-ticket__original text-xs text-[#71827e] line-through"
        >
          {{ formatVnd(item.original_price) }}
        </p>
        <p class="market-flash-ticket__sold mt-2 text-xs font-semibold text-slate-500">
          Đã bán {{ item.sold_count }}/{{ item.quota }} · Còn
          {{ flashSaleAvailableQuantity(item) }}
        </p>
        <button
          class="market-flash-ticket__action market-primary-action mt-3 w-full px-3 py-2 text-xs disabled:pointer-events-none disabled:bg-slate-300 disabled:text-slate-600"
          type="button"
          :disabled="flashSaleAvailableQuantity(item) <= 0 || addingVariantId !== null"
          @click="addItem(item)"
        >
          <span class="market-flash-ticket__action-full">
            {{
              flashSaleAvailableQuantity(item) <= 0
                ? 'Hết hàng'
                : addingVariantId === item.variant
                  ? 'Đang thêm…'
                  : 'Thêm vào giỏ'
            }}
          </span>
          <span class="market-flash-ticket__action-short">
            {{
              flashSaleAvailableQuantity(item) <= 0
                ? 'Hết'
                : addingVariantId === item.variant
                  ? '…'
                  : 'Thêm'
            }}
          </span>
        </button>
      </article>
    </div>
  </section>
</template>
