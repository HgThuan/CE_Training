<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import QASection from './QASection.vue'
import { afterSalesApi } from '@/features/after-sales/api'
import type { Review } from '@/features/after-sales/types'
import type { PublicProductDetail } from '../types'

type TabId = 'description' | 'qa' | 'reviews'

const props = defineProps<{ product: PublicProductDetail }>()
const route = useRoute()
const router = useRouter()
const tabs: Array<{ id: TabId; label: string }> = [
  { id: 'description', label: 'Mô tả' },
  { id: 'qa', label: 'Hỏi đáp' },
  { id: 'reviews', label: 'Đánh giá' },
]
const activeTab = ref<TabId>('description')
const reviews = ref<Review[]>([])
const reviewError = ref('')
const reviewsLoaded = ref(false)

async function loadReviews(): Promise<void> {
  if (reviewsLoaded.value) return
  try {
    reviews.value = (await afterSalesApi.productReviews(props.product.id)).data.data
    reviewsLoaded.value = true
  } catch {
    reviewError.value = 'Không thể tải đánh giá lúc này.'
  }
}

function tabFromHash(hash: string): TabId {
  const value = hash.replace('#', '')
  return tabs.some((tab) => tab.id === value) ? (value as TabId) : 'description'
}

async function selectTab(tab: TabId, focus = false): Promise<void> {
  activeTab.value = tab
  await router.replace({ hash: `#${tab}` })
  if (focus) {
    await nextTick()
    document.getElementById(`product-tab-${tab}`)?.focus()
  }
}

function handleTabKeydown(event: KeyboardEvent): void {
  const currentIndex = tabs.findIndex((tab) => tab.id === activeTab.value)
  let nextIndex = currentIndex
  if (event.key === 'ArrowRight') nextIndex = (currentIndex + 1) % tabs.length
  else if (event.key === 'ArrowLeft') nextIndex = (currentIndex - 1 + tabs.length) % tabs.length
  else if (event.key === 'Home') nextIndex = 0
  else if (event.key === 'End') nextIndex = tabs.length - 1
  else return
  event.preventDefault()
  void selectTab(tabs[nextIndex]!.id, true)
}

watch(
  () => route.hash,
  (hash) => {
    activeTab.value = tabFromHash(hash)
  },
  { immediate: true },
)
watch(
  activeTab,
  (tab) => {
    if (tab === 'reviews') void loadReviews()
  },
  { immediate: true },
)
</script>

<template>
  <section class="rounded-3xl bg-white p-5 ring-1 ring-slate-200 sm:p-8">
    <div
      class="flex gap-2 overflow-x-auto border-b border-slate-200"
      role="tablist"
      aria-label="Thông tin sản phẩm"
      @keydown="handleTabKeydown"
    >
      <button
        v-for="tab in tabs"
        :id="`product-tab-${tab.id}`"
        :key="tab.id"
        class="shrink-0 border-b-2 px-4 py-3 text-sm font-bold transition"
        :class="
          activeTab === tab.id
            ? 'border-indigo-600 text-indigo-700'
            : 'border-transparent text-slate-500 hover:text-slate-900'
        "
        type="button"
        role="tab"
        :aria-selected="activeTab === tab.id"
        :aria-controls="`product-panel-${tab.id}`"
        :tabindex="activeTab === tab.id ? 0 : -1"
        @click="selectTab(tab.id)"
      >
        {{ tab.label }}
      </button>
    </div>

    <div
      v-if="activeTab === 'description'"
      id="product-panel-description"
      class="pt-7"
      role="tabpanel"
      aria-labelledby="product-tab-description"
      tabindex="0"
    >
      <h2 class="text-2xl font-black">Mô tả sản phẩm</h2>
      <p class="mt-5 whitespace-pre-line leading-8 text-slate-700">
        {{ product.description || product.short_description || 'Sản phẩm chưa có mô tả.' }}
      </p>
    </div>

    <div
      v-else-if="activeTab === 'qa'"
      id="product-panel-qa"
      class="pt-7"
      role="tabpanel"
      aria-labelledby="product-tab-qa"
      tabindex="0"
    >
      <QASection :product-id="product.id" />
    </div>

    <div
      v-else
      id="product-panel-reviews"
      class="py-7"
      role="tabpanel"
      aria-labelledby="product-tab-reviews"
      tabindex="0"
    >
      <h2 class="text-2xl font-black">Đánh giá sản phẩm</h2>
      <p v-if="reviewError" class="mt-3 text-rose-700">{{ reviewError }}</p>
      <p v-else-if="!reviews.length" class="mt-3 text-slate-600">Sản phẩm chưa có đánh giá.</p>
      <article v-for="review in reviews" :key="review.id" class="mt-5 border-t pt-5">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div>
            <b>{{ review.customer_name || 'Khách hàng' }}</b
            ><span
              v-if="review.is_verified_purchase"
              class="ml-2 rounded-full bg-emerald-50 px-2 py-1 text-xs font-bold text-emerald-700"
              >Đã mua hàng</span
            >
          </div>
          <b class="text-amber-500">{{ '★'.repeat(review.rating) }}</b>
        </div>
        <p class="mt-3 text-slate-700">
          {{ review.content || 'Khách hàng không để lại bình luận.' }}
        </p>
        <div v-if="review.media.length" class="mt-3 flex gap-2">
          <a
            v-for="media in review.media"
            :key="media.id"
            :href="media.file_url"
            target="_blank"
            class="rounded-lg border px-3 py-2 text-sm font-bold text-indigo-700"
            >{{ media.media_type === 'IMAGE' ? 'Xem ảnh' : 'Xem video' }}</a
          >
        </div>
        <blockquote v-if="review.reply" class="mt-4 rounded-xl bg-indigo-50 p-4 text-sm">
          <b>Phản hồi từ shop:</b> {{ review.reply.content }}
        </blockquote>
      </article>
    </div>
  </section>
</template>
