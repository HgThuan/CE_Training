<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import FormMessage from '@/features/auth/components/FormMessage.vue'
import { getErrorMessage } from '@/features/auth/errors'
import { productApi } from '@/features/product/api'
import { readBrowsingHistory } from '@/features/product/browsingHistory'
import ProductRecommendationCarousel from '@/features/product/components/ProductRecommendationCarousel.vue'
import type { PublicProductListItem } from '@/features/product/types'
import { useAuthStore } from '@/stores/auth'

import { homeApi } from '../api'
import type { HomePageData } from '../types'
import CategoryShowcase from './CategoryShowcase.vue'
import FlashSaleSection from './FlashSaleSection.vue'
import HeroBanner from './HeroBanner.vue'
import MarketCuratedHero from './MarketCuratedHero.vue'
import ProductGrid from './ProductGrid.vue'

const authStore = useAuthStore()
const data = ref<HomePageData | null>(null)
const loading = ref(true)
const errorMessage = ref('')
const personalizedProducts = ref<PublicProductListItem[]>([])
const recommendationsLoading = ref(false)
let recommendationRequestSequence = 0

const heroBanners = computed(
  () => data.value?.banners.filter((banner) => banner.position === 'hero') ?? [],
)
const middleBanners = computed(
  () => data.value?.banners.filter((banner) => banner.position === 'middle') ?? [],
)

async function loadHome(): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  try {
    data.value = (await homeApi.get()).data.data
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
}

async function loadPersonalizedRecommendations(): Promise<void> {
  const sequence = ++recommendationRequestSequence
  const userId = authStore.user?.id
  personalizedProducts.value = []
  recommendationsLoading.value = false

  if (!authStore.initialized || !authStore.isAuthenticated || userId === undefined) return

  recommendationsLoading.value = true
  try {
    const response = await productApi.homeRecommendations(readBrowsingHistory(userId))
    if (
      sequence === recommendationRequestSequence &&
      authStore.isAuthenticated &&
      authStore.user?.id === userId
    ) {
      personalizedProducts.value = response.data.data.results
    }
  } catch {
    // Personalized recommendations are optional and must not block the home page.
  } finally {
    if (sequence === recommendationRequestSequence) recommendationsLoading.value = false
  }
}

watch(
  () => [authStore.initialized, authStore.isAuthenticated, authStore.user?.id] as const,
  () => void loadPersonalizedRecommendations(),
  { immediate: true },
)

onMounted(loadHome)

onBeforeUnmount(() => {
  recommendationRequestSequence += 1
})
</script>

<template>
  <div class="min-h-screen bg-[#f7f3ea] text-[#0b2a25]">
    <main class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:py-8">
      <FormMessage v-if="errorMessage" :message="errorMessage" />
      <div v-if="errorMessage" class="mt-4">
        <button
          class="rounded-xl bg-slate-950 px-5 py-3 text-sm font-bold text-white hover:bg-indigo-700"
          type="button"
          @click="loadHome"
        >
          Thử tải lại
        </button>
      </div>

      <div v-if="loading" class="space-y-12" aria-label="Đang tải trang chủ">
        <div class="aspect-[16/7] min-h-64 animate-pulse rounded-[2rem] bg-slate-200" />
        <div>
          <div class="h-8 w-64 animate-pulse rounded bg-slate-200" />
          <div class="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
            <div
              v-for="index in 6"
              :key="index"
              class="aspect-square animate-pulse rounded-2xl bg-slate-200"
            />
          </div>
        </div>
        <div class="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          <div
            v-for="index in 4"
            :key="index"
            class="overflow-hidden rounded-3xl bg-white ring-1 ring-slate-200"
          >
            <div class="aspect-[4/3] animate-pulse bg-slate-200" />
            <div class="space-y-3 p-5">
              <div class="h-4 animate-pulse rounded bg-slate-100" />
              <div class="h-5 w-2/3 animate-pulse rounded bg-slate-200" />
            </div>
          </div>
        </div>
      </div>

      <template v-else-if="data">
        <MarketCuratedHero />

        <div class="mt-6 space-y-10 lg:mt-8 lg:space-y-12">
          <FlashSaleSection />
          <CategoryShowcase :categories="data.categories" />
          <ProductRecommendationCarousel
            v-if="authStore.isAuthenticated"
            title="Gợi ý cho bạn"
            :products="personalizedProducts"
            :loading="recommendationsLoading"
          />
          <ProductGrid
            title="Sản phẩm mới"
            description="Những lựa chọn vừa xuất hiện trên Mercato."
            :products="data.new_arrivals"
            empty-message="Sản phẩm mới đang được cập nhật."
          />
          <HeroBanner
            v-if="[...heroBanners, ...middleBanners].length"
            :banners="[...heroBanners, ...middleBanners]"
            compact
          />
          <ProductGrid
            title="Bán chạy"
            description="Các sản phẩm được khách hàng yêu thích gần đây."
            :products="data.best_sellers"
            empty-message="Danh sách bán chạy đang được cập nhật."
          />
        </div>
      </template>
    </main>

    <footer class="market-receipt mt-16 bg-[#173b35] text-white">
      <div
        class="mx-auto grid max-w-7xl gap-5 px-4 py-9 text-sm sm:grid-cols-[1fr_auto] sm:items-center sm:px-6"
      >
        <div>
          <p class="font-display text-2xl">Mercato</p>
          <p class="mt-1 text-[#d8e5e0]">
            Một nơi để tìm kiếm, mua sắm và theo dõi đơn từ nhiều gian hàng.
          </p>
        </div>
        <div class="flex flex-wrap gap-4 font-bold">
          <RouterLink class="text-[#f2c14e]" to="/products">Khám phá sản phẩm</RouterLink>
          <RouterLink class="text-white" to="/voucher-center">Voucher</RouterLink>
          <RouterLink class="text-white" to="/account/orders">Đơn hàng</RouterLink>
        </div>
      </div>
    </footer>
  </div>
</template>
