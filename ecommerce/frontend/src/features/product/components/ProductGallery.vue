<script setup lang="ts">
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  MagnifyingGlassPlusIcon,
  PhotoIcon,
  PlayCircleIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import type { ProductMedia } from '../types'

const props = defineProps<{ media: ProductMedia[]; productName: string }>()

const activeIndex = ref(0)
const imageFailed = ref(false)
const lightboxOpen = ref(false)
const activeMedia = computed(() => props.media[activeIndex.value] ?? null)
const imageIndexes = computed(() =>
  props.media.flatMap((item, index) => (item.media_type === 'image' ? [index] : [])),
)

watch(
  () => props.media,
  () => {
    activeIndex.value = 0
    imageFailed.value = false
    closeLightbox()
  },
)

function move(direction: number): void {
  if (!props.media.length) return
  activeIndex.value = (activeIndex.value + direction + props.media.length) % props.media.length
  imageFailed.value = false
}

function moveLightbox(direction: number): void {
  if (!imageIndexes.value.length) return
  const currentPosition = Math.max(imageIndexes.value.indexOf(activeIndex.value), 0)
  const nextPosition =
    (currentPosition + direction + imageIndexes.value.length) % imageIndexes.value.length
  activeIndex.value = imageIndexes.value[nextPosition]!
  imageFailed.value = false
}

function choose(index: number): void {
  activeIndex.value = index
  imageFailed.value = false
}

function openLightbox(): void {
  if (activeMedia.value?.media_type !== 'image' || imageFailed.value) return
  lightboxOpen.value = true
  document.body.style.overflow = 'hidden'
}

function closeLightbox(): void {
  lightboxOpen.value = false
  document.body.style.overflow = ''
}

function handleKeyboard(event: KeyboardEvent): void {
  if (!lightboxOpen.value) return
  if (event.key === 'Escape') closeLightbox()
  else if (event.key === 'ArrowLeft') moveLightbox(-1)
  else if (event.key === 'ArrowRight') moveLightbox(1)
}

watch(lightboxOpen, (open) => {
  if (open) window.addEventListener('keydown', handleKeyboard)
  else window.removeEventListener('keydown', handleKeyboard)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeyboard)
  document.body.style.overflow = ''
})
</script>

<template>
  <section aria-label="Thư viện media sản phẩm">
    <div
      class="relative grid aspect-square place-items-center overflow-hidden rounded-[2rem] bg-slate-100 ring-1 ring-slate-200"
    >
      <button
        v-if="activeMedia?.media_type === 'image' && !imageFailed"
        class="group h-full w-full cursor-zoom-in"
        type="button"
        aria-label="Phóng to ảnh sản phẩm"
        @click="openLightbox"
      >
        <img
          :src="activeMedia.file_url"
          :alt="activeMedia.alt_text || productName"
          class="h-full w-full object-contain"
          loading="eager"
          decoding="async"
          fetchpriority="high"
          @error="imageFailed = true"
        />
        <span
          class="absolute bottom-4 right-4 inline-flex items-center gap-2 rounded-full bg-white/90 px-3 py-2 text-xs font-bold text-slate-800 opacity-0 shadow-lg backdrop-blur transition group-hover:opacity-100 group-focus-visible:opacity-100"
        >
          <MagnifyingGlassPlusIcon class="h-4 w-4" />
          Phóng to
        </span>
      </button>
      <video
        v-else-if="activeMedia?.media_type === 'video'"
        :src="activeMedia.file_url"
        :poster="activeMedia.thumbnail_url ?? undefined"
        class="h-full w-full object-contain"
        controls
        playsinline
        preload="metadata"
      />
      <div v-else class="grid place-items-center gap-3 text-slate-400">
        <PhotoIcon class="h-16 w-16" aria-hidden="true" />
        <span class="text-sm font-semibold">
          {{ imageFailed ? 'Không thể tải hình ảnh' : 'Chưa có hình ảnh' }}
        </span>
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

    <div v-if="media.length > 1" class="mt-4 flex gap-3 overflow-x-auto pb-2">
      <button
        v-for="(item, index) in media"
        :key="item.id"
        class="relative grid h-20 w-20 shrink-0 place-items-center overflow-hidden rounded-2xl bg-slate-100 ring-2 ring-offset-2 transition"
        :class="index === activeIndex ? 'ring-indigo-600' : 'ring-transparent hover:ring-slate-300'"
        type="button"
        :aria-label="`Xem media ${index + 1}`"
        :aria-current="index === activeIndex ? 'true' : undefined"
        @click="choose(index)"
      >
        <img
          v-if="item.media_type === 'image'"
          :src="item.thumbnail_url || item.file_url"
          :alt="item.alt_text || `${productName} ${index + 1}`"
          class="h-full w-full object-cover"
          loading="lazy"
          decoding="async"
        />
        <template v-else>
          <img
            v-if="item.thumbnail_url"
            :src="item.thumbnail_url"
            :alt="`Video ${productName} ${index + 1}`"
            class="h-full w-full object-cover"
            loading="lazy"
            decoding="async"
          />
          <PlayCircleIcon v-else class="h-9 w-9 text-slate-500" aria-hidden="true" />
          <span
            class="absolute inset-x-1 bottom-1 rounded bg-slate-950/70 py-0.5 text-[10px] font-bold text-white"
          >
            VIDEO
          </span>
        </template>
      </button>
    </div>

    <Teleport to="body">
      <div
        v-if="lightboxOpen && activeMedia?.media_type === 'image'"
        class="fixed inset-0 z-[100] grid place-items-center bg-slate-950/95 p-4"
        role="dialog"
        aria-modal="true"
        aria-label="Ảnh sản phẩm phóng to"
      >
        <button
          class="absolute inset-0 cursor-zoom-out"
          type="button"
          aria-label="Đóng ảnh phóng to"
          @click="closeLightbox"
        />
        <img
          :src="activeMedia.file_url"
          :alt="activeMedia.alt_text || productName"
          class="relative z-10 max-h-[92vh] max-w-[92vw] object-contain"
          decoding="async"
        />
        <button
          class="absolute right-5 top-5 z-20 grid h-11 w-11 place-items-center rounded-full bg-white/10 text-white hover:bg-white/20"
          type="button"
          aria-label="Đóng"
          @click="closeLightbox"
        >
          <XMarkIcon class="h-6 w-6" />
        </button>
        <template v-if="imageIndexes.length > 1">
          <button
            class="absolute left-4 z-20 grid h-12 w-12 place-items-center rounded-full bg-white/10 text-white hover:bg-white/20 sm:left-8"
            type="button"
            aria-label="Ảnh trước"
            @click="moveLightbox(-1)"
          >
            <ChevronLeftIcon class="h-7 w-7" />
          </button>
          <button
            class="absolute right-4 z-20 grid h-12 w-12 place-items-center rounded-full bg-white/10 text-white hover:bg-white/20 sm:right-8"
            type="button"
            aria-label="Ảnh tiếp theo"
            @click="moveLightbox(1)"
          >
            <ChevronRightIcon class="h-7 w-7" />
          </button>
        </template>
      </div>
    </Teleport>
  </section>
</template>
