<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import QASection from './QASection.vue'
import type { PublicProductDetail } from '../types'

type TabId = 'description' | 'qa' | 'reviews'

defineProps<{ product: PublicProductDetail }>()
const route = useRoute()
const router = useRouter()
const tabs: Array<{ id: TabId; label: string }> = [
  { id: 'description', label: 'Mô tả' },
  { id: 'qa', label: 'Hỏi đáp' },
  { id: 'reviews', label: 'Đánh giá' },
]
const activeTab = ref<TabId>('description')

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
      class="py-12 text-center"
      role="tabpanel"
      aria-labelledby="product-tab-reviews"
      tabindex="0"
    >
      <h2 class="text-2xl font-black">Đánh giá sản phẩm</h2>
      <p class="mx-auto mt-3 max-w-xl leading-7 text-slate-600">
        Dữ liệu đánh giá xác thực sẽ được triển khai ở Sprint 08. Điểm đánh giá tổng hợp hiện vẫn
        được hiển thị trong phần thông tin sản phẩm.
      </p>
    </div>
  </section>
</template>
