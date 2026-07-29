<script setup lang="ts">
import { MagnifyingGlassIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import { onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { searchApi } from '../api'
import type { SearchSuggestion } from '../types'
import AiSearchToggle from './AiSearchToggle.vue'

withDefaults(
  defineProps<{
    placeholder?: string
  }>(),
  {
    placeholder: 'Tìm sản phẩm, thương hiệu hoặc gian hàng…',
  },
)

const route = useRoute()
const router = useRouter()
const root = ref<HTMLElement | null>(null)
const query = ref(typeof route.query.q === 'string' ? route.query.q : '')
const suggestions = ref<SearchSuggestion[]>([])
const loading = ref(false)
const open = ref(false)
const activeIndex = ref(-1)
const suggestionError = ref('')
const aiEnabled = ref(isAiQueryEnabled(route.query.ai))
let debounceTimer: number | undefined
let requestSequence = 0

function isAiQueryEnabled(value: unknown): boolean {
  return typeof value === 'string' && ['true', '1'].includes(value.toLowerCase())
}

function cancelPending(): void {
  requestSequence += 1
  if (debounceTimer !== undefined) window.clearTimeout(debounceTimer)
  debounceTimer = undefined
  loading.value = false
}

async function loadSuggestions(searchTerm: string, sequence: number): Promise<void> {
  loading.value = true
  suggestionError.value = ''
  try {
    const response = await searchApi.suggestions(searchTerm)
    if (sequence !== requestSequence || query.value.trim() !== searchTerm) return
    suggestions.value = response.data.data
    activeIndex.value = -1
    open.value = true
  } catch {
    if (sequence !== requestSequence) return
    suggestions.value = []
    suggestionError.value = 'Không thể tải gợi ý.'
    open.value = true
  } finally {
    if (sequence === requestSequence) loading.value = false
  }
}

watch(query, (value) => {
  cancelPending()
  suggestions.value = []
  activeIndex.value = -1
  suggestionError.value = ''
  const searchTerm = value.trim()
  if (searchTerm.length < 2) {
    open.value = false
    return
  }
  const sequence = requestSequence
  debounceTimer = window.setTimeout(() => loadSuggestions(searchTerm, sequence), 250)
})

watch(
  () => route.query.q,
  (value) => {
    const routeQuery = typeof value === 'string' ? value : ''
    if (routeQuery !== query.value) query.value = routeQuery
  },
)

watch(
  () => route.query.ai,
  (value) => {
    aiEnabled.value = isAiQueryEnabled(value)
  },
)

async function submitSearch(): Promise<void> {
  const searchTerm = query.value.trim()
  if (!searchTerm) return
  cancelPending()
  open.value = false
  await router.push({
    path: '/search',
    query: { q: searchTerm, ai: aiEnabled.value ? 'true' : undefined },
  })
}

async function toggleAiSearch(enabled: boolean): Promise<void> {
  aiEnabled.value = enabled
  if (route.path !== '/search') return

  await router.push({
    path: '/search',
    query: {
      ...route.query,
      ai: enabled ? 'true' : undefined,
      page: undefined,
    },
  })
}

async function chooseSuggestion(suggestion: SearchSuggestion): Promise<void> {
  query.value = suggestion.text
  await submitSearch()
}

function handleKeyboard(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    open.value = false
    activeIndex.value = -1
    return
  }
  if (!suggestions.value.length) {
    if (event.key === 'Enter') void submitSearch()
    return
  }
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    open.value = true
    activeIndex.value = (activeIndex.value + 1) % suggestions.value.length
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    open.value = true
    activeIndex.value =
      (activeIndex.value - 1 + suggestions.value.length) % suggestions.value.length
  } else if (event.key === 'Enter') {
    event.preventDefault()
    const selected = suggestions.value[activeIndex.value]
    if (selected) void chooseSuggestion(selected)
    else void submitSearch()
  }
}

function handleFocusOut(event: FocusEvent): void {
  const nextTarget = event.relatedTarget
  if (!(nextTarget instanceof Node) || !root.value?.contains(nextTarget)) {
    open.value = false
    activeIndex.value = -1
  }
}

function clearSearch(): void {
  query.value = ''
  suggestions.value = []
  open.value = false
}

onBeforeUnmount(cancelPending)
</script>

<template>
  <form
    ref="root"
    class="relative w-full"
    role="search"
    @submit.prevent="submitSearch"
    @focusout="handleFocusOut"
  >
    <div class="flex items-center gap-2">
      <label class="relative min-w-0 flex-1">
        <span class="sr-only">Tìm kiếm sản phẩm</span>
        <MagnifyingGlassIcon
          class="pointer-events-none absolute left-3.5 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400"
        />
        <input
          v-model="query"
          class="h-11 w-full rounded-xl border border-slate-300 bg-white pl-11 pr-20 text-sm outline-none transition focus:border-indigo-600 focus:ring-4 focus:ring-indigo-100"
          type="search"
          role="combobox"
          autocomplete="off"
          :placeholder="placeholder"
          :aria-expanded="open"
          aria-controls="search-suggestions"
          :aria-activedescendant="activeIndex >= 0 ? `search-suggestion-${activeIndex}` : undefined"
          @focus="query.trim().length >= 2 && (open = true)"
          @keydown="handleKeyboard"
        />
        <button
          v-if="query"
          class="absolute right-11 top-1/2 grid h-8 w-8 -translate-y-1/2 place-items-center rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-700"
          type="button"
          aria-label="Xóa từ khóa"
          @click="clearSearch"
        >
          <XMarkIcon class="h-4 w-4" />
        </button>
        <button
          class="absolute right-1.5 top-1/2 grid h-8 w-8 -translate-y-1/2 place-items-center rounded-lg bg-slate-950 text-white hover:bg-indigo-700"
          type="submit"
          aria-label="Tìm kiếm"
        >
          <MagnifyingGlassIcon class="h-4 w-4" />
        </button>
      </label>
      <AiSearchToggle :model-value="aiEnabled" compact @update:model-value="toggleAiSearch" />
    </div>

    <div
      v-if="open"
      id="search-suggestions"
      class="absolute inset-x-0 top-[calc(100%+0.5rem)] z-50 overflow-hidden rounded-2xl bg-white shadow-2xl ring-1 ring-slate-200"
      role="listbox"
    >
      <p v-if="loading" class="px-4 py-4 text-sm text-slate-500">Đang tìm gợi ý…</p>
      <p v-else-if="suggestionError" class="px-4 py-4 text-sm text-rose-700">
        {{ suggestionError }}
      </p>
      <template v-else-if="suggestions.length">
        <button
          v-for="(suggestion, index) in suggestions"
          :id="`search-suggestion-${index}`"
          :key="`${suggestion.text}-${index}`"
          class="flex w-full items-center gap-3 px-4 py-3 text-left text-sm hover:bg-indigo-50"
          :class="index === activeIndex ? 'bg-indigo-50 text-indigo-900' : 'text-slate-700'"
          type="button"
          role="option"
          :aria-selected="index === activeIndex"
          @mouseenter="activeIndex = index"
          @click="chooseSuggestion(suggestion)"
        >
          <MagnifyingGlassIcon class="h-4 w-4 shrink-0 text-slate-400" />
          <span class="truncate">{{ suggestion.text }}</span>
        </button>
      </template>
      <p v-else class="px-4 py-4 text-sm text-slate-500">Không có gợi ý phù hợp.</p>
    </div>
  </form>
</template>
