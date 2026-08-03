<script setup lang="ts">
import {
  BuildingStorefrontIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  StarIcon,
  UsersIcon,
} from '@heroicons/vue/24/outline'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import FormMessage from '@/features/auth/components/FormMessage.vue'
import { getErrorMessage } from '@/features/auth/errors'
import ProductCard from '@/features/product/components/ProductCard.vue'
import VoucherCard from '@/features/promotion/components/VoucherCard.vue'
import { promotionApi } from '@/features/promotion/api'
import type { Voucher } from '@/features/promotion/types'
import type { PaginationMeta } from '@/shared/types/api'
import { useAuthStore } from '@/stores/auth'

import { shopApi } from '../api'
import type { PublicShopData, PublicShopSort } from '../types'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const data = ref<PublicShopData | null>(null)
const meta = ref<PaginationMeta>({
  page: 1,
  page_size: 12,
  total_items: 0,
  total_pages: 0,
})
const loading = ref(true)
const following = ref(false)
const errorMessage = ref('')
const followMessage = ref('')
const shopVouchers = ref<Voucher[]>([])
const voucherNotice = ref('')
let requestSequence = 0

const page = computed(() => Math.max(Number(route.query.page) || 1, 1))
const sort = computed<PublicShopSort>(() => {
  const value = route.query.sort
  return ['newest', 'price_asc', 'price_desc', 'rating'].includes(String(value))
    ? (value as PublicShopSort)
    : 'newest'
})
const followDisabled = computed(
  () => following.value || Boolean(authStore.user && authStore.user.role !== 'customer'),
)

async function loadShopVouchers(shopId: number): Promise<void> {
  try {
    shopVouchers.value = (await promotionApi.shopVouchers(shopId)).data.data
  } catch {
    shopVouchers.value = []
  }
}

async function loadShop(): Promise<void> {
  const sequence = ++requestSequence
  loading.value = true
  errorMessage.value = ''
  followMessage.value = ''
  try {
    const response = await shopApi.getPublicShop(
      String(route.params.slug),
      page.value,
      sort.value,
      12,
    )
    if (sequence !== requestSequence) return
    data.value = response.data.data
    void loadShopVouchers(data.value.shop.id)
    meta.value =
      response.data.meta ??
      ({
        page: page.value,
        page_size: 12,
        total_items: data.value.products.length,
        total_pages: data.value.products.length ? 1 : 0,
      } satisfies PaginationMeta)
  } catch (error) {
    if (sequence === requestSequence) {
      data.value = null
      errorMessage.value = getErrorMessage(error)
    }
  } finally {
    if (sequence === requestSequence) loading.value = false
  }
}

async function collectVoucher(voucher: Voucher): Promise<void> {
  if (!authStore.isAuthenticated) {
    await router.push({ name: 'login', query: { redirect: route.fullPath } })
    return
  }
  voucher.is_collected = true
  try {
    await promotionApi.collectVoucher(voucher.id, crypto.randomUUID())
    voucherNotice.value = `Đã lưu ${voucher.code}.`
  } catch {
    voucher.is_collected = false
    voucherNotice.value = 'Không thể lưu voucher này.'
  }
}

async function changeSort(event: Event): Promise<void> {
  const nextSort = (event.target as HTMLSelectElement).value as PublicShopSort
  await router.push({
    name: 'public-shop',
    params: { slug: route.params.slug },
    query: { sort: nextSort === 'newest' ? undefined : nextSort },
  })
}

async function changePage(nextPage: number): Promise<void> {
  if (nextPage < 1 || nextPage > meta.value.total_pages || nextPage === meta.value.page) return
  await router.push({
    name: 'public-shop',
    params: { slug: route.params.slug },
    query: {
      sort: sort.value === 'newest' ? undefined : sort.value,
      page: nextPage > 1 ? String(nextPage) : undefined,
    },
  })
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

async function toggleFollow(): Promise<void> {
  followMessage.value = ''
  if (!authStore.user) {
    await router.push({
      name: 'login',
      query: { redirect: route.fullPath },
    })
    return
  }
  if (authStore.user.role !== 'customer' || !data.value) {
    followMessage.value = 'Chỉ tài khoản Customer có thể theo dõi gian hàng.'
    return
  }

  following.value = true
  try {
    const result = (await shopApi.toggleFollow(data.value.shop.id)).data.data
    if (data.value.shop.id === result.shop_id) {
      data.value.shop.is_following = result.is_following
      data.value.shop.follower_count = result.follower_count
    }
    followMessage.value = result.is_following
      ? 'Đã theo dõi gian hàng.'
      : 'Đã bỏ theo dõi gian hàng.'
  } catch (error) {
    followMessage.value = getErrorMessage(error)
  } finally {
    following.value = false
  }
}

watch(
  () => [String(route.params.slug), route.query.page, route.query.sort] as const,
  () => void loadShop(),
  { immediate: true },
)

onBeforeUnmount(() => {
  requestSequence += 1
})
</script>

<template>
  <main class="min-h-[70vh] bg-slate-50 pb-16">
    <div v-if="loading" aria-label="Đang tải gian hàng">
      <div class="aspect-[10/3] min-h-48 w-full animate-pulse bg-slate-200" />
      <div class="mx-auto -mt-10 max-w-7xl px-4 sm:px-6">
        <div class="h-40 animate-pulse rounded-3xl bg-white shadow-sm" />
        <div class="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          <div
            v-for="index in 8"
            :key="index"
            class="aspect-[4/3] animate-pulse rounded-3xl bg-slate-200"
          />
        </div>
      </div>
    </div>

    <section v-else-if="data">
      <div class="relative aspect-[10/3] min-h-48 max-h-[480px] w-full overflow-hidden">
        <img
          v-if="data.shop.cover_url"
          :src="data.shop.cover_url"
          :alt="`Ảnh bìa ${data.shop.name}`"
          class="h-full w-full object-cover"
          fetchpriority="high"
        />
        <div
          v-else
          class="h-full w-full bg-gradient-to-r from-indigo-700 via-violet-600 to-fuchsia-600"
        />
      </div>

      <div class="mx-auto -mt-10 max-w-7xl px-4 sm:-mt-14 sm:px-6">
        <section class="relative rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200 sm:p-7">
          <div class="flex flex-col gap-5 sm:flex-row sm:items-end">
            <img
              v-if="data.shop.logo_url"
              :alt="data.shop.name"
              class="h-24 w-24 rounded-2xl bg-white object-cover ring-4 ring-white sm:h-28 sm:w-28"
              :src="data.shop.logo_url"
              loading="lazy"
              decoding="async"
            />
            <span
              v-else
              class="grid h-24 w-24 place-items-center rounded-2xl bg-slate-100 text-slate-500 ring-4 ring-white sm:h-28 sm:w-28"
            >
              <BuildingStorefrontIcon class="h-12 w-12" aria-hidden="true" />
            </span>

            <div class="min-w-0 flex-1">
              <p class="text-sm font-bold uppercase tracking-[0.2em] text-indigo-600">Gian hàng</p>
              <h1 class="mt-1 text-3xl font-black tracking-tight sm:text-4xl">
                {{ data.shop.name }}
              </h1>
              <p v-if="data.shop.description" class="mt-3 max-w-3xl leading-7 text-slate-600">
                {{ data.shop.description }}
              </p>
              <div class="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-sm text-slate-600">
                <span class="inline-flex items-center gap-1.5">
                  <StarIcon class="h-5 w-5 fill-amber-400 text-amber-400" aria-hidden="true" />
                  <strong class="text-slate-900">{{ data.shop.average_rating }}</strong>
                </span>
                <span>{{ data.shop.total_products }} sản phẩm</span>
                <span class="inline-flex items-center gap-1.5">
                  <UsersIcon class="h-5 w-5 text-indigo-600" aria-hidden="true" />
                  {{ data.shop.follower_count }} người theo dõi
                </span>
              </div>
            </div>

            <button
              class="min-h-11 rounded-xl px-5 py-3 text-sm font-bold transition disabled:cursor-not-allowed disabled:opacity-50"
              :class="
                data.shop.is_following
                  ? 'border border-slate-300 bg-white text-slate-700 hover:bg-slate-50'
                  : 'bg-indigo-600 text-white hover:bg-indigo-700'
              "
              type="button"
              :aria-pressed="data.shop.is_following"
              :aria-busy="following"
              :disabled="followDisabled"
              @click="toggleFollow"
            >
              {{
                following ? 'Đang cập nhật…' : data.shop.is_following ? 'Đang theo dõi' : 'Theo dõi'
              }}
            </button>
          </div>
          <p class="sr-only" aria-live="polite">{{ followMessage }}</p>
        </section>

        <section v-if="shopVouchers.length" class="mt-8">
          <div class="flex items-center justify-between">
            <h2 class="text-xl font-black">Voucher của shop</h2>
            <RouterLink class="text-sm font-bold text-indigo-600" to="/voucher-center">
              Xem tất cả
            </RouterLink>
          </div>
          <p v-if="voucherNotice" class="mt-2 text-sm font-bold text-emerald-700">
            {{ voucherNotice }}
          </p>
          <div class="mt-3 grid gap-3 md:grid-cols-2">
            <VoucherCard
              v-for="voucher in shopVouchers.slice(0, 4)"
              :key="voucher.id"
              :voucher="voucher"
              :collected="voucher.is_collected"
              compact
              @collect="collectVoucher"
            />
          </div>
        </section>

        <section class="mt-10">
          <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 class="text-2xl font-black">Sản phẩm</h2>
              <p class="mt-1 text-sm text-slate-500">
                {{ meta.total_items }} lựa chọn đang hiển thị
              </p>
            </div>
            <label class="flex items-center gap-3 text-sm font-semibold">
              <span>Sắp xếp</span>
              <select
                :value="sort"
                class="min-h-11 flex-1 rounded-xl border border-slate-300 bg-white px-3 sm:flex-none"
                @change="changeSort"
              >
                <option value="newest">Mới nhất</option>
                <option value="price_asc">Giá tăng dần</option>
                <option value="price_desc">Giá giảm dần</option>
                <option value="rating">Đánh giá cao</option>
              </select>
            </label>
          </div>

          <div
            v-if="data.products.length"
            class="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
          >
            <ProductCard v-for="product in data.products" :key="product.id" :product="product" />
          </div>
          <div
            v-else
            class="mt-6 rounded-3xl border border-dashed border-slate-300 bg-white p-12 text-center text-slate-500"
          >
            Gian hàng chưa có sản phẩm công khai.
          </div>

          <nav
            v-if="meta.total_pages > 1"
            class="mt-10 flex items-center justify-center gap-3"
            aria-label="Phân trang sản phẩm gian hàng"
          >
            <button
              class="grid h-11 w-11 place-items-center rounded-xl border border-slate-300 bg-white disabled:opacity-40"
              type="button"
              aria-label="Trang trước"
              :disabled="meta.page <= 1"
              @click="changePage(meta.page - 1)"
            >
              <ChevronLeftIcon class="h-5 w-5" />
            </button>
            <span class="text-sm text-slate-600">
              Trang <strong>{{ meta.page }}</strong> / {{ meta.total_pages }}
            </span>
            <button
              class="grid h-11 w-11 place-items-center rounded-xl border border-slate-300 bg-white disabled:opacity-40"
              type="button"
              aria-label="Trang sau"
              :disabled="meta.page >= meta.total_pages"
              @click="changePage(meta.page + 1)"
            >
              <ChevronRightIcon class="h-5 w-5" />
            </button>
          </nav>
        </section>
      </div>
    </section>

    <section v-else class="mx-auto max-w-3xl px-4 py-16 sm:px-6">
      <FormMessage v-if="errorMessage" :message="errorMessage" />
      <button
        class="mt-4 rounded-xl bg-slate-950 px-5 py-3 text-sm font-bold text-white hover:bg-indigo-700"
        type="button"
        @click="loadShop"
      >
        Thử tải lại
      </button>
    </section>
  </main>
</template>
