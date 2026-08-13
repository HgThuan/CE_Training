<script setup lang="ts">
import { computed } from 'vue'

import { useCartStore } from '@/features/cart/store'
import { formatVnd } from '@/shared/lib/formatters'

import FlashSaleCountdown from '../../components/FlashSaleCountdown.vue'
import { usePromotionStore } from '../../store'

const store = usePromotionStore()
const cartStore = useCartStore()
const sales = computed(() => store.flashSales.filter((sale) => sale.status === 'ongoing'))
void store.loadActiveFlashSales()
</script>

<template>
  <main class="mx-auto min-h-[70vh] max-w-7xl px-4 py-10 sm:px-6">
    <h1 class="text-4xl font-black">Flash Sale đang diễn ra</h1>
    <p class="mt-2 text-slate-500">Giá và quota được xác nhận lại ở máy chủ khi xem giỏ.</p>
    <div v-if="store.loading" class="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <div v-for="i in 4" :key="i" class="h-80 animate-pulse rounded-3xl bg-slate-200" />
    </div>
    <section v-else-if="store.error" class="mt-8 rounded-3xl bg-rose-50 p-8 text-center">
      <p class="font-bold text-rose-800">{{ store.error }}</p>
      <button
        class="mt-4 rounded-xl bg-rose-700 px-4 py-2 font-bold text-white"
        @click="store.loadActiveFlashSales"
      >
        Thử lại
      </button>
    </section>
    <section
      v-else-if="!sales.length"
      class="mt-8 rounded-3xl border border-dashed bg-white p-12 text-center text-slate-500"
    >
      Hiện chưa có Flash Sale đang chạy.
    </section>
    <section v-for="sale in sales" v-else :key="sale.id" class="mt-8">
      <header class="flex flex-wrap items-center justify-between gap-3">
        <h2 class="text-2xl font-black">{{ sale.name }}</h2>
        <p class="rounded-xl bg-slate-950 px-4 py-2 text-sm text-white">
          Còn <FlashSaleCountdown :end-time="sale.end_time" @ended="store.loadActiveFlashSales" />
        </p>
      </header>
      <div class="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <article
          v-for="item in sale.items"
          :key="item.id"
          class="rounded-3xl border bg-white p-4 shadow-sm"
        >
          <img
            :src="item.primary_image || 'https://placehold.co/400x300?text=Flash+Sale'"
            :alt="item.product_name"
            class="aspect-square w-full rounded-2xl object-cover"
          />
          <h3 class="mt-3 font-black">{{ item.product_name }}</h3>
          <p class="mt-2 text-xl font-black text-rose-600">{{ formatVnd(item.sale_price) }}</p>
          <p class="text-sm text-slate-400 line-through">{{ formatVnd(item.original_price) }}</p>
          <p class="mt-2 text-sm text-slate-500">Đã bán {{ item.sold_count }}/{{ item.quota }}</p>
          <button
            class="mt-4 w-full rounded-xl bg-slate-950 px-4 py-2.5 font-bold text-white"
            @click="
              cartStore.addItem(item.variant, 1, {
                product_slug: item.product_slug ?? '',
                product_name: item.product_name ?? 'Flash Sale',
                variant_name: item.variant_sku,
                image: item.primary_image,
                price: item.sale_price,
              })
            "
          >
            Thêm vào giỏ
          </button>
        </article>
      </div>
    </section>
  </main>
</template>
