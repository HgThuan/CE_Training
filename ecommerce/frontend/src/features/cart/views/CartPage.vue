<script setup lang="ts">
import { ShoppingBagIcon } from '@heroicons/vue/24/outline'
import { onMounted } from 'vue'

import { useCartStore } from '../store'
import type { CartItem } from '../types'
import CartShopGroup from '../components/CartShopGroup.vue'
import CartSummaryBar from '../components/CartSummaryBar.vue'
import VoucherInput from '../components/VoucherInput.vue'

const store = useCartStore()

async function updateItem(
  item: CartItem,
  payload: { quantity?: number; is_selected?: boolean },
): Promise<void> {
  try {
    await store.updateItem(item, payload)
  } catch {
    // The store exposes the backend message in the retry banner.
  }
}

onMounted(() => void store.load())
</script>

<template>
  <main class="mx-auto min-h-[70vh] max-w-7xl px-4 py-8 sm:px-6 lg:py-12">
    <div class="mb-7 flex flex-wrap items-end justify-between gap-3">
      <div>
        <p class="text-sm font-bold uppercase tracking-widest text-indigo-600">CUS-13</p>
        <h1 class="mt-1 text-3xl font-black tracking-tight text-slate-950 sm:text-4xl">
          Giỏ hàng của bạn
        </h1>
      </div>
      <p v-if="!store.isAuthenticatedCustomer" class="text-sm text-slate-500">
        Giỏ khách được lưu an toàn trên trình duyệt và sẽ gộp sau khi đăng nhập.
      </p>
    </div>

    <div v-if="store.loading" class="space-y-4" aria-label="Đang tải giỏ hàng">
      <div v-for="index in 2" :key="index" class="h-44 animate-pulse rounded-3xl bg-slate-200" />
    </div>

    <section
      v-else-if="store.error"
      class="rounded-3xl border border-rose-200 bg-rose-50 p-8 text-center"
    >
      <p class="font-bold text-rose-800">{{ store.error }}</p>
      <button
        class="mt-4 rounded-xl bg-rose-700 px-4 py-2 font-bold text-white"
        @click="store.load"
      >
        Thử lại
      </button>
    </section>

    <section
      v-else-if="!store.cart?.shops.length"
      class="rounded-3xl border border-dashed border-slate-300 bg-white p-12 text-center"
    >
      <ShoppingBagIcon class="mx-auto h-14 w-14 text-slate-300" />
      <h2 class="mt-4 text-xl font-black">Giỏ hàng đang trống</h2>
      <p class="mt-2 text-slate-500">Khám phá sản phẩm và chọn món bạn yêu thích.</p>
      <RouterLink
        class="mt-5 inline-block rounded-xl bg-indigo-600 px-5 py-3 font-bold text-white"
        to="/products"
      >
        Tiếp tục mua sắm
      </RouterLink>
    </section>

    <div v-else class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
      <div class="space-y-5">
        <p
          v-if="store.mergeWarning"
          class="rounded-2xl bg-amber-50 px-4 py-3 text-sm font-bold text-amber-900"
        >
          {{ store.mergeWarning }}
        </p>
        <p
          v-if="store.error"
          class="rounded-2xl bg-rose-50 px-4 py-3 text-sm font-bold text-rose-800"
        >
          {{ store.error }}
        </p>
        <CartShopGroup
          v-for="group in store.cart.shops"
          :key="group.shop_id"
          :group="group"
          @update="updateItem"
          @remove="store.removeItem"
        />
      </div>

      <div class="space-y-5">
        <VoucherInput
          v-if="store.isAuthenticatedCustomer"
          :platform-code="store.platformVoucher"
          :shop-codes="store.shopVouchers"
          :shops="store.cart.shops"
          :loading="store.previewing"
          :error="store.previewError"
          @update:platform-code="store.platformVoucher = $event"
          @update:shop-code="(shopId, value) => (store.shopVouchers[shopId] = value)"
          @apply="store.calculatePreview"
        />
        <CartSummaryBar
          :selected-count="store.selectedValidItems.length"
          :selected-total="store.selectedTotal"
          :preview="store.preview"
          :disabled="store.selectedValidItems.length === 0"
          @preview="store.calculatePreview"
        />
      </div>
    </div>
  </main>
</template>
