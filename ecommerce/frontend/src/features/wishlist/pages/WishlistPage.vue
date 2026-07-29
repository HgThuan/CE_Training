<script setup lang="ts">
import { HeartIcon } from '@heroicons/vue/24/outline'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import FormMessage from '@/features/auth/components/FormMessage.vue'
import { getErrorMessage } from '@/features/auth/errors'
import ProductCard from '@/features/product/components/ProductCard.vue'
import { formatVnd } from '@/shared/lib/formatters'

import { useWishlistStore } from '../store'

const route = useRoute()
const router = useRouter()
const wishlistStore = useWishlistStore()
const errorMessage = ref('')
let requestSequence = 0

const currentPage = computed(() => Math.max(Number(route.query.page) || 1, 1))

async function loadWishlist(): Promise<void> {
  const sequence = ++requestSequence
  errorMessage.value = ''
  try {
    await wishlistStore.loadPage(currentPage.value, 12)
  } catch (error) {
    if (sequence === requestSequence) errorMessage.value = getErrorMessage(error)
  }
}

async function changePage(page: number): Promise<void> {
  if (page < 1 || page > wishlistStore.meta.total_pages || page === wishlistStore.meta.page) {
    return
  }
  await router.push({
    name: 'wishlist',
    query: { page: page > 1 ? String(page) : undefined },
  })
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

watch(
  () => route.query.page,
  () => void loadWishlist(),
  { immediate: true },
)

onBeforeUnmount(() => {
  requestSequence += 1
})
</script>

<template>
  <main class="mx-auto min-h-[70vh] max-w-7xl px-4 py-8 sm:px-6 lg:py-12">
    <div class="max-w-3xl">
      <p class="text-sm font-bold uppercase tracking-[0.2em] text-rose-600">Wishlist</p>
      <h1 class="mt-2 text-3xl font-black tracking-tight sm:text-5xl">Sản phẩm yêu thích</h1>
      <p class="mt-4 leading-7 text-slate-600">
        Lưu lại những lựa chọn bạn quan tâm và theo dõi mức giá tại thời điểm thêm.
      </p>
    </div>

    <FormMessage v-if="errorMessage" class="mt-6" :message="errorMessage" />
    <button
      v-if="errorMessage"
      class="mt-3 text-sm font-bold text-indigo-700"
      type="button"
      @click="loadWishlist"
    >
      Thử tải lại
    </button>

    <div
      v-if="wishlistStore.loading"
      class="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
      aria-label="Đang tải wishlist"
    >
      <div
        v-for="index in 8"
        :key="index"
        class="overflow-hidden rounded-3xl bg-white ring-1 ring-slate-200"
      >
        <div class="aspect-[4/3] animate-pulse bg-slate-200" />
        <div class="space-y-3 p-5">
          <div class="h-4 animate-pulse rounded bg-slate-200" />
          <div class="h-5 w-2/3 animate-pulse rounded bg-slate-200" />
        </div>
      </div>
    </div>

    <section
      v-else-if="wishlistStore.items.length"
      class="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
      aria-live="polite"
    >
      <div v-for="item in wishlistStore.items" :key="item.id">
        <ProductCard :product="item.product" />
        <p class="mt-2 px-2 text-xs text-slate-500">
          Giá khi thêm:
          <strong class="text-slate-700">{{ formatVnd(item.price_when_added) }}</strong>
        </p>
      </div>
    </section>

    <section
      v-else-if="!errorMessage"
      class="mt-10 rounded-3xl border border-dashed border-slate-300 bg-white px-6 py-16 text-center"
    >
      <HeartIcon class="mx-auto h-12 w-12 text-slate-400" aria-hidden="true" />
      <h2 class="mt-4 text-xl font-black">Wishlist đang trống</h2>
      <p class="mt-2 text-slate-600">Nhấn biểu tượng trái tim để lưu sản phẩm bạn yêu thích.</p>
      <RouterLink
        class="mt-6 inline-flex rounded-xl bg-slate-950 px-5 py-3 font-bold text-white hover:bg-indigo-700"
        to="/products"
      >
        Khám phá sản phẩm
      </RouterLink>
    </section>

    <nav
      v-if="!wishlistStore.loading && wishlistStore.meta.total_pages > 1"
      class="mt-10 flex items-center justify-center gap-3"
      aria-label="Phân trang wishlist"
    >
      <button
        class="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold disabled:opacity-40"
        type="button"
        :disabled="wishlistStore.meta.page <= 1"
        @click="changePage(wishlistStore.meta.page - 1)"
      >
        Trước
      </button>
      <span class="text-sm text-slate-600">
        Trang <strong>{{ wishlistStore.meta.page }}</strong> /
        {{ wishlistStore.meta.total_pages }}
      </span>
      <button
        class="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-bold disabled:opacity-40"
        type="button"
        :disabled="wishlistStore.meta.page >= wishlistStore.meta.total_pages"
        @click="changePage(wishlistStore.meta.page + 1)"
      >
        Sau
      </button>
    </nav>
  </main>
</template>
