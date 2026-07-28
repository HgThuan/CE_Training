<script setup lang="ts">
import { ChevronLeftIcon, ChevronRightIcon, PhotoIcon } from '@heroicons/vue/24/outline'
import { computed, ref, watch } from 'vue'

import type { ProductMedia } from '../types'

const props = defineProps<{ media: ProductMedia[]; productName: string }>()

const activeIndex = ref(0)
const activeMedia = computed(() => props.media[activeIndex.value] ?? null)

watch(
  () => props.media,
  () => {
    activeIndex.value = 0
  },
)

function move(direction: number): void {
  if (!props.media.length) return
  activeIndex.value = (activeIndex.value + direction + props.media.length) % props.media.length
}
</script>

<template>
  <section aria-label="Thư viện media sản phẩm">
    <div
      class="relative grid aspect-square place-items-center overflow-hidden rounded-[2rem] bg-slate-100 ring-1 ring-slate-200"
    >
      <img
        v-if="activeMedia?.media_type === 'image'"
        :src="activeMedia.file_url"
        :alt="activeMedia.alt_text || productName"
        class="h-full w-full object-contain"
      />
      <video
        v-else-if="activeMedia"
        :src="activeMedia.file_url"
        :poster="activeMedia.thumbnail_url ?? undefined"
        class="h-full w-full object-contain"
        controls
        playsinline
      />
      <div v-else class="grid place-items-center gap-3 text-slate-400">
        <PhotoIcon class="h-16 w-16" aria-hidden="true" />
        <span class="text-sm font-semibold">Chưa có hình ảnh</span>
      </div>
      <template v-if="media.length > 1">
        <button
          class="absolute left-4 grid h-11 w-11 place-items-center rounded-full bg-white/90 text-slate-900 shadow-lg backdrop-blur hover:bg-white"
          type="button"
          aria-label="Media trước"
          @click="move(-1)"
        >
          <ChevronLeftIcon class="h-5 w-5" />
        </button>
        <button
          class="absolute right-4 grid h-11 w-11 place-items-center rounded-full bg-white/90 text-slate-900 shadow-lg backdrop-blur hover:bg-white"
          type="button"
          aria-label="Media tiếp theo"
          @click="move(1)"
        >
          <ChevronRightIcon class="h-5 w-5" />
        </button>
      </template>
    </div>
    <div v-if="media.length > 1" class="mt-4 flex gap-3 overflow-x-auto pb-1">
      <button
        v-for="(item, index) in media"
        :key="item.id"
        class="relative h-20 w-20 shrink-0 overflow-hidden rounded-2xl bg-slate-100 ring-2 ring-offset-2 transition"
        :class="index === activeIndex ? 'ring-indigo-600' : 'ring-transparent hover:ring-slate-300'"
        type="button"
        :aria-label="`Xem media ${index + 1}`"
        @click="activeIndex = index"
      >
        <img
          v-if="item.media_type === 'image'"
          :src="item.thumbnail_url || item.file_url"
          :alt="item.alt_text || `${productName} ${index + 1}`"
          class="h-full w-full object-cover"
        />
        <video v-else :src="item.file_url" class="h-full w-full object-cover" muted />
        <span
          v-if="item.media_type === 'video'"
          class="absolute inset-x-1 bottom-1 rounded bg-slate-950/70 py-0.5 text-[10px] font-bold text-white"
        >
          VIDEO
        </span>
      </button>
    </div>
  </section>
</template>
