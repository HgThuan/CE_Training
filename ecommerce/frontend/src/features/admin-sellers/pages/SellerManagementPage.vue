<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ActiveSellerWorkspace from '../components/ActiveSellerWorkspace.vue'
import SellerApplicationWorkspace from '../components/SellerApplicationWorkspace.vue'

type SellerTab = 'pending' | 'active' | 'rejected'
const route = useRoute()
const router = useRouter()
const tabs: Array<{ value: SellerTab; label: string; description: string }> = [
  { value: 'pending', label: 'Chờ duyệt', description: 'Kiểm tra hồ sơ và giấy tờ seller mới' },
  {
    value: 'active',
    label: 'Đang hoạt động',
    description: 'Quản lý seller và trạng thái gian hàng',
  },
  { value: 'rejected', label: 'Đã từ chối', description: 'Tra cứu hồ sơ và lý do đã từ chối' },
]
const activeTab = computed<SellerTab>(() => {
  const tab = String(route.query.tab ?? 'active')
  return tabs.some((item) => item.value === tab) ? (tab as SellerTab) : 'active'
})
function selectTab(tab: SellerTab): void {
  void router.replace({ query: { ...route.query, tab } })
}
</script>

<template>
  <main class="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:py-10">
    <div class="max-w-3xl">
      <h1 class="text-3xl font-black tracking-tight text-slate-950 sm:text-4xl">
        Quản lý nhà bán hàng
      </h1>
      <p class="mt-3 text-slate-600">
        Một nơi để duyệt hồ sơ mới, quản lý seller đang hoạt động và tra cứu các quyết định trước
        đây.
      </p>
    </div>
    <div class="mt-8 border-b border-slate-200" role="tablist" aria-label="Nhóm trạng thái seller">
      <div class="flex gap-1 overflow-x-auto">
        <button
          v-for="tab in tabs"
          :key="tab.value"
          class="min-w-max border-b-2 px-4 py-3 text-left transition-colors"
          :class="
            activeTab === tab.value
              ? 'border-indigo-600 text-indigo-700'
              : 'border-transparent text-slate-500 hover:text-slate-900'
          "
          type="button"
          role="tab"
          :aria-selected="activeTab === tab.value"
          @click="selectTab(tab.value)"
        >
          <span class="block font-bold">{{ tab.label }}</span
          ><span class="mt-0.5 hidden text-xs font-normal sm:block">{{ tab.description }}</span>
        </button>
      </div>
    </div>
    <ActiveSellerWorkspace v-if="activeTab === 'active'" />
    <SellerApplicationWorkspace v-else :status="activeTab" />
  </main>
</template>
