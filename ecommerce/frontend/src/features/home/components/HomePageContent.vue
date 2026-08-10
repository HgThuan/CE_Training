<script setup lang="ts">
import { ArrowRightIcon, SparklesIcon } from '@heroicons/vue/24/outline'
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
  <div class="min-h-screen bg-[#f8fafc] text-slate-900">
    <main class="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:py-12">
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
        <HeroBanner v-if="heroBanners.length" :banners="heroBanners" />
        <section
          v-else
          class="overflow-hidden rounded-[2rem] bg-slate-950 px-6 py-14 text-white sm:px-12 sm:py-20"
        >
          <SparklesIcon class="h-10 w-10 text-indigo-300" />
          <p class="mt-6 text-sm font-bold uppercase tracking-[0.2em] text-indigo-300">
            Mercato marketplace
          </p>
          <h1 class="mt-3 max-w-3xl text-4xl font-black tracking-tight sm:text-6xl">
            Khám phá sản phẩm dành cho bạn
          </h1>
          <p class="mt-5 max-w-2xl leading-7 text-slate-300 sm:text-lg">
            Mua sắm từ các gian hàng và sản phẩm đã được kiểm duyệt trên toàn hệ thống.
          </p>
          <RouterLink
            class="mt-8 inline-flex items-center gap-2 rounded-xl bg-white px-5 py-3 font-bold text-slate-950"
            to="/products"
          >
            Khám phá sản phẩm
            <ArrowRightIcon class="h-5 w-5" />
          </RouterLink>
        </section>

        <div class="mt-14 space-y-16 lg:mt-20 lg:space-y-24">
          <CategoryShowcase :categories="data.categories" />
          <FlashSaleSection />
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
          <HeroBanner v-if="middleBanners.length" :banners="middleBanners" compact />
          <ProductGrid
            title="Bán chạy"
            description="Các sản phẩm được khách hàng yêu thích gần đây."
            :products="data.best_sellers"
            empty-message="Danh sách bán chạy đang được cập nhật."
          />
        </div>
      </template>
    </main>

    <footer class="mt-16 border-t border-slate-200 bg-white">
      <div
        class="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-8 text-sm text-slate-500 sm:px-6"
      >
        <p>© 2026 Mercato</p>
        <RouterLink class="font-bold text-indigo-700" to="/products">Khám phá catalog</RouterLink>
      </div>
    </footer>
  </div>
</template>
