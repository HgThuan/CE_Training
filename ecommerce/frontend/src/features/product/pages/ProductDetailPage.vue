<script setup lang="ts">
import {
  BuildingStorefrontIcon,
  ChatBubbleLeftRightIcon,
  CheckBadgeIcon,
  MinusIcon,
  PlusIcon,
  ShieldCheckIcon,
  ShoppingBagIcon,
  StarIcon,
  TruckIcon,
} from '@heroicons/vue/24/outline'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import FormMessage from '@/features/auth/components/FormMessage.vue'
import { useCartStore } from '@/features/cart/store'
import { getErrorMessage } from '@/features/auth/errors'
import WaitlistButton from '@/features/inventory/components/WaitlistButton.vue'
import WishlistToggleButton from '@/features/wishlist/components/WishlistToggleButton.vue'
import { formatVnd } from '@/shared/lib/formatters'
import { useAuthStore } from '@/stores/auth'

import { productApi } from '../api'
import { readBrowsingHistory, recordBrowsingProduct } from '../browsingHistory'
import ProductDetailTabs from '../components/ProductDetailTabs.vue'
import ProductGallery from '../components/ProductGallery.vue'
import ProductRecommendationCarousel from '../components/ProductRecommendationCarousel.vue'
import VariantSelector from '../components/VariantSelector.vue'
import { useProductStore } from '../store'
import type { ProductVariant, PublicProductListItem } from '../types'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const cartStore = useCartStore()
const productStore = useProductStore()
const errorMessage = ref('')
const selectedVariant = ref<ProductVariant | null>(null)
const quantity = ref(1)
const cartNotice = ref('')
const similarProducts = ref<PublicProductListItem[]>([])
const recommendedProducts = ref<PublicProductListItem[]>([])
const similarLoading = ref(false)
const recommendationsLoading = ref(false)
let pageRequestSequence = 0

const product = computed(() => productStore.detail)
const galleryMedia = computed(() => {
  if (!product.value) return []
  const baseMedia = product.value.media.filter((media) => !media.variant_id)
  if (!selectedVariant.value) return baseMedia
  return [
    ...product.value.media.filter((media) => media.variant_id === selectedVariant.value?.id),
    ...baseMedia,
  ]
})
const displayPrice = computed(() => {
  if (selectedVariant.value) return formatVnd(selectedVariant.value.sale_price)
  if (!product.value) return ''
  if (product.value.min_price === product.value.max_price) return formatVnd(product.value.min_price)
  return `${formatVnd(product.value.min_price)} – ${formatVnd(product.value.max_price)}`
})
const displayRegularPrice = computed(() => {
  if (
    selectedVariant.value?.is_flash_sale &&
    Number(selectedVariant.value.regular_price) > Number(selectedVariant.value.sale_price)
  )
    return formatVnd(selectedVariant.value.regular_price)
  if (
    !selectedVariant.value &&
    product.value?.is_flash_sale &&
    Number(product.value.regular_min_price) > Number(product.value.min_price)
  )
    return formatVnd(product.value.regular_min_price)
  return ''
})
const maximumQuantity = computed(() => {
  const stock = selectedVariant.value?.available_stock ?? 0
  const flashQuota = selectedVariant.value?.remaining_flash_quota
  return Math.min(99, stock, flashQuota ?? stock)
})
const canAdd = computed(
  () =>
    Boolean(product.value && selectedVariant.value) &&
    maximumQuantity.value > 0 &&
    quantity.value >= 1 &&
    quantity.value <= maximumQuantity.value,
)

function updateQuantity(amount: number): void {
  quantity.value = Math.min(maximumQuantity.value, Math.max(1, quantity.value + amount))
}

function handleVariantChange(variant: ProductVariant | null): void {
  selectedVariant.value = variant
  quantity.value = 1
}

async function prepareCart(action: 'cart' | 'buy'): Promise<void> {
  if (!product.value || !selectedVariant.value) return
  try {
    await cartStore.addItem(selectedVariant.value.id, quantity.value, {
      product_slug: product.value.slug,
      shop_slug: product.value.shop.slug,
      product_name: product.value.name,
      variant_name: selectedVariant.value.name,
      image: galleryMedia.value[0]?.file_url ?? null,
      price: selectedVariant.value.sale_price,
    })
    cartNotice.value =
      action === 'cart'
        ? `Đã thêm ${quantity.value} sản phẩm vào giỏ.`
        : 'Đã thêm sản phẩm. Đang mở giỏ hàng...'
    if (action === 'buy') await router.push({ name: 'cart' })
  } catch {
    cartNotice.value = cartStore.error
  }
}

function isCurrentProductRequest(sequence: number, productId: string): boolean {
  return sequence === pageRequestSequence && product.value?.id === productId
}

async function loadProductRecommendations(sequence: number, productId: string): Promise<void> {
  const browsingHistory = readBrowsingHistory(authStore.user?.id)
  similarLoading.value = true
  recommendationsLoading.value = true

  const similarRequest = productApi
    .similar(productId)
    .then((response) => {
      if (isCurrentProductRequest(sequence, productId)) {
        similarProducts.value = response.data.data.results
      }
    })
    .finally(() => {
      if (isCurrentProductRequest(sequence, productId)) similarLoading.value = false
    })

  const recommendationRequest = productApi
    .recommendations(productId, browsingHistory)
    .then((response) => {
      if (isCurrentProductRequest(sequence, productId)) {
        recommendedProducts.value = response.data.data.results
      }
    })
    .finally(() => {
      if (isCurrentProductRequest(sequence, productId)) recommendationsLoading.value = false
    })

  recordBrowsingProduct(productId, authStore.user?.id)
  await Promise.allSettled([similarRequest, recommendationRequest])
}

async function loadProduct(): Promise<void> {
  const sequence = ++pageRequestSequence
  errorMessage.value = ''
  selectedVariant.value = null
  quantity.value = 1
  cartNotice.value = ''
  similarProducts.value = []
  recommendedProducts.value = []
  similarLoading.value = false
  recommendationsLoading.value = false
  try {
    await productStore.loadDetail(
      String(route.params.slug),
      typeof route.query.shop === 'string' ? route.query.shop : undefined,
    )
    if (sequence !== pageRequestSequence) return
    const loadedProduct = product.value
    if (!loadedProduct) return
    if (!loadedProduct.attributes.length) {
      selectedVariant.value =
        loadedProduct.variants.find((variant) => variant.available_stock > 0) ??
        loadedProduct.variants[0] ??
        null
    }
    await loadProductRecommendations(sequence, loadedProduct.id)
  } catch (error) {
    if (sequence === pageRequestSequence) errorMessage.value = getErrorMessage(error)
  }
}

watch(
  () =>
    [
      String(route.params.slug),
      typeof route.query.shop === 'string' ? route.query.shop : '',
    ] as const,
  () => void loadProduct(),
  { immediate: true },
)

onBeforeUnmount(() => {
  pageRequestSequence += 1
})
</script>

<template>
  <div class="min-h-screen bg-[#f8fafc]">
    <main class="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:py-12">
      <nav aria-label="Đường dẫn điều hướng" class="text-sm font-semibold text-slate-500">
        <ol class="flex min-w-0 flex-wrap items-center gap-2">
          <li><RouterLink class="hover:text-indigo-700" to="/">Trang chủ</RouterLink></li>
          <li aria-hidden="true">/</li>
          <li><RouterLink class="hover:text-indigo-700" to="/products">Sản phẩm</RouterLink></li>
          <template v-if="product">
            <li aria-hidden="true">/</li>
            <li>
              <RouterLink
                class="hover:text-indigo-700"
                :to="{ name: 'product-list', query: { category: product.category.id } }"
              >
                {{ product.category.name }}
              </RouterLink>
            </li>
            <li aria-hidden="true">/</li>
            <li class="max-w-full truncate text-slate-800" aria-current="page">
              {{ product.name }}
            </li>
          </template>
        </ol>
      </nav>

      <div v-if="errorMessage" class="mt-6">
        <FormMessage :message="errorMessage" />
        <button
          class="mt-3 text-sm font-bold text-indigo-700 hover:text-indigo-900"
          type="button"
          @click="loadProduct"
        >
          Thử tải lại
        </button>
      </div>

      <div v-if="productStore.loading" class="mt-8 grid animate-pulse gap-10 lg:grid-cols-2">
        <div class="aspect-square rounded-[2rem] bg-slate-200" />
        <div class="space-y-5 pt-4">
          <div class="h-4 w-1/4 rounded bg-slate-200" />
          <div class="h-12 rounded bg-slate-200" />
          <div class="h-8 w-1/3 rounded bg-slate-200" />
          <div class="h-32 rounded bg-slate-200" />
        </div>
      </div>

      <template v-else-if="product">
        <div class="mt-8 grid gap-10 lg:grid-cols-[1.05fr_0.95fr] lg:gap-14">
          <ProductGallery :media="galleryMedia" :product-name="product.name" />

          <section class="market-panel p-5 sm:p-8 lg:sticky lg:top-36 lg:self-start">
            <div class="flex flex-wrap items-center gap-2 text-sm font-semibold">
              <span class="rounded-full bg-indigo-50 px-3 py-1 text-indigo-700">
                {{ product.category.name }}
              </span>
              <span v-if="product.brand" class="rounded-full bg-slate-100 px-3 py-1 text-slate-700">
                {{ product.brand.name }}
              </span>
            </div>
            <div class="mt-5 flex items-start gap-3">
              <h1
                class="min-w-0 flex-1 text-3xl font-black tracking-tight text-slate-950 sm:text-5xl"
              >
                {{ product.name }}
              </h1>
              <WishlistToggleButton
                class="shrink-0"
                :product-id="product.id"
                :product-name="product.name"
              />
            </div>
            <div class="mt-5 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-slate-600">
              <span class="inline-flex items-center gap-1.5">
                <StarIcon class="h-5 w-5 fill-amber-400 text-amber-400" />
                <strong class="text-slate-950">{{
                  Number(product.rating_average).toFixed(1)
                }}</strong>
                ({{ product.rating_count }} đánh giá)
              </span>
              <span>{{ product.sold_count }} đã bán</span>
              <span class="inline-flex items-center gap-1 text-emerald-700">
                <CheckBadgeIcon class="h-5 w-5" />
                Đã kiểm duyệt
              </span>
            </div>
            <p class="mt-7 text-3xl font-black tracking-tight text-[#e85d3f]">
              {{ displayPrice }}
            </p>
            <div v-if="displayRegularPrice" class="mt-2 flex flex-wrap items-center gap-3">
              <span class="text-lg text-slate-400 line-through">{{ displayRegularPrice }}</span>
              <span class="rounded-full bg-rose-100 px-3 py-1 text-xs font-black text-rose-700">
                FLASH SALE
                <template v-if="selectedVariant?.remaining_flash_quota != null">
                  · còn {{ selectedVariant?.remaining_flash_quota }}
                </template>
              </span>
            </div>
            <p v-if="product.short_description" class="mt-5 leading-7 text-slate-600">
              {{ product.short_description }}
            </p>

            <div class="my-8 h-px bg-slate-200" />

            <VariantSelector
              v-if="product.attributes.length"
              :attributes="product.attributes"
              :variants="product.variants"
              @change="handleVariantChange"
            />

            <fieldset v-else-if="product.variants.length > 1" class="mt-8">
              <legend class="text-sm font-bold text-slate-900">Chọn phiên bản</legend>
              <div class="mt-3 flex flex-wrap gap-2.5">
                <button
                  v-for="variant in product.variants"
                  :key="variant.id"
                  class="min-h-11 rounded-xl border px-4 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400 disabled:line-through"
                  :class="
                    selectedVariant?.id === variant.id
                      ? 'border-indigo-600 bg-indigo-50 text-indigo-700 ring-1 ring-indigo-600'
                      : 'border-slate-300 bg-white text-slate-700 hover:border-slate-500'
                  "
                  type="button"
                  :disabled="variant.available_stock === 0"
                  @click="handleVariantChange(variant)"
                >
                  {{ variant.name || variant.sku }} · {{ formatVnd(variant.sale_price) }}
                </button>
              </div>
            </fieldset>

            <div class="mt-8 flex flex-wrap items-center gap-4">
              <div
                class="inline-flex h-12 items-center rounded-xl border border-slate-300 bg-white p-1"
                aria-label="Số lượng"
              >
                <button
                  class="grid h-10 w-10 place-items-center rounded-lg hover:bg-slate-100 disabled:opacity-40"
                  type="button"
                  aria-label="Giảm số lượng"
                  :disabled="quantity === 1"
                  @click="updateQuantity(-1)"
                >
                  <MinusIcon class="h-4 w-4" />
                </button>
                <span class="w-10 text-center font-bold">{{ quantity }}</span>
                <button
                  class="grid h-10 w-10 place-items-center rounded-lg hover:bg-slate-100"
                  type="button"
                  aria-label="Tăng số lượng"
                  :disabled="quantity >= maximumQuantity"
                  @click="updateQuantity(1)"
                >
                  <PlusIcon class="h-4 w-4" />
                </button>
              </div>
              <button
                class="inline-flex h-12 flex-1 items-center justify-center gap-2 rounded-xl border-2 border-[#173b35] px-5 font-bold text-[#173b35] transition hover:bg-[#e8eee9] disabled:cursor-not-allowed disabled:border-slate-300 disabled:text-slate-400"
                type="button"
                :disabled="!canAdd"
                @click="prepareCart('cart')"
              >
                <ShoppingBagIcon class="h-5 w-5" />
                Thêm vào giỏ
              </button>
              <button
                class="market-primary-action h-12 flex-1 px-5 disabled:cursor-not-allowed disabled:bg-slate-300"
                type="button"
                :disabled="!canAdd"
                @click="prepareCart('buy')"
              >
                Mua ngay
              </button>
            </div>

            <p v-if="selectedVariant" class="mt-3 text-sm font-semibold text-slate-600">
              {{
                selectedVariant.available_stock > 0
                  ? `Còn ${selectedVariant.available_stock} sản phẩm`
                  : 'Biến thể này đã hết hàng'
              }}
            </p>
            <WaitlistButton
              v-if="selectedVariant && selectedVariant.available_stock === 0"
              :variant-id="selectedVariant.id"
            />

            <p
              v-if="cartNotice"
              class="mt-4 rounded-xl bg-indigo-50 px-4 py-3 text-sm font-semibold text-indigo-900"
              role="status"
            >
              {{ cartNotice }}
            </p>

            <div class="mt-8 grid gap-3 sm:grid-cols-3">
              <div class="rounded-2xl bg-white p-4 text-center ring-1 ring-slate-200">
                <TruckIcon class="mx-auto h-6 w-6 text-indigo-600" />
                <p class="mt-2 text-xs font-bold text-slate-700">Giao hàng toàn quốc</p>
              </div>
              <div class="rounded-2xl bg-white p-4 text-center ring-1 ring-slate-200">
                <ShieldCheckIcon class="mx-auto h-6 w-6 text-indigo-600" />
                <p class="mt-2 text-xs font-bold text-slate-700">Mua sắm an tâm</p>
              </div>
              <div class="rounded-2xl bg-white p-4 text-center ring-1 ring-slate-200">
                <CheckBadgeIcon class="mx-auto h-6 w-6 text-indigo-600" />
                <p class="mt-2 text-xs font-bold text-slate-700">Shop xác thực</p>
              </div>
            </div>
          </section>
        </div>

        <section class="mt-12 grid gap-6 lg:grid-cols-[1fr_340px]">
          <ProductDetailTabs :product="product" />
          <aside
            class="group rounded-3xl bg-slate-950 p-6 text-white transition hover:bg-indigo-700"
          >
            <RouterLink
              :to="{ name: 'public-shop', params: { slug: product.shop.slug } }"
              class="block"
            >
              <div class="flex items-center gap-4">
                <img
                  v-if="product.shop.logo_url"
                  :src="product.shop.logo_url"
                  :alt="product.shop.name"
                  class="h-14 w-14 rounded-2xl bg-white object-cover"
                  loading="lazy"
                  decoding="async"
                />
                <span v-else class="grid h-14 w-14 place-items-center rounded-2xl bg-white/10">
                  <BuildingStorefrontIcon class="h-7 w-7" />
                </span>
                <div>
                  <p class="text-xs font-bold uppercase tracking-widest text-indigo-200">Nhà bán</p>
                  <h2 class="mt-1 font-black">{{ product.shop.name }}</h2>
                </div>
              </div>
              <p class="mt-6 text-sm text-slate-300 group-hover:text-white">
                Xem gian hàng và các sản phẩm khác →
              </p>
            </RouterLink>
            <RouterLink
              v-if="authStore.user?.role === 'customer'"
              class="mt-4 inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2.5 text-sm font-black text-slate-950"
              :to="{
                name: 'customer-chat',
                query: { shop: product.shop.slug, product: product.id },
              }"
            >
              <ChatBubbleLeftRightIcon class="h-5 w-5" /> Chat với shop
            </RouterLink>
          </aside>
        </section>

        <div class="mt-16 space-y-16 lg:mt-24 lg:space-y-24">
          <ProductRecommendationCarousel
            title="Sản phẩm tương tự"
            :products="similarProducts"
            :loading="similarLoading"
          />
          <ProductRecommendationCarousel
            title="Gợi ý dành cho bạn"
            :products="recommendedProducts"
            :loading="recommendationsLoading"
          />
        </div>
      </template>
    </main>
  </div>
</template>
