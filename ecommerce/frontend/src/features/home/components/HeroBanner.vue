<script setup lang="ts">
import { ChevronLeftIcon, ChevronRightIcon, PhotoIcon } from '@heroicons/vue/24/outline'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'

import type { HomeBanner } from '../types'

const props = withDefaults(
  defineProps<{
    banners: HomeBanner[]
    compact?: boolean
  }>(),
  {
    compact: false,
  },
)

const activeIndex = ref(0)
const imageFailed = ref(false)
const paused = ref(false)
let timer: number | undefined

const activeBanner = computed(() => props.banners[activeIndex.value] ?? null)

function stopAutoplay(): void {
  if (timer !== undefined) window.clearInterval(timer)
  timer = undefined
}

function startAutoplay(): void {
  stopAutoplay()
  if (
    props.banners.length <= 1 ||
    paused.value ||
    window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  ) {
    return
  }
  timer = window.setInterval(() => move(1, false), 6000)
}

function move(direction: number, restart = true): void {
  if (!props.banners.length) return
  activeIndex.value = (activeIndex.value + direction + props.banners.length) % props.banners.length
  imageFailed.value = false
  if (restart) startAutoplay()
}

function goTo(index: number): void {
  activeIndex.value = index
  imageFailed.value = false
  startAutoplay()
}

function pause(): void {
  paused.value = true
  stopAutoplay()
}

function resume(): void {
  paused.value = false
  startAutoplay()
}

watch(
  () => props.banners,
  () => {
    activeIndex.value = 0
    imageFailed.value = false
    startAutoplay()
  },
)

onMounted(startAutoplay)
onUnmounted(stopAutoplay)
</script>

<template>
  <section
    v-if="activeBanner"
    class="relative overflow-hidden bg-[#173b35] text-white shadow-[0_16px_40px_rgba(23,59,53,0.14)]"
    :class="compact ? 'rounded-2xl' : 'rounded-2xl'"
    aria-label="Banner khuyến mại"
    aria-roledescription="carousel"
    @mouseenter="pause"
    @mouseleave="resume"
    @focusin="pause"
    @focusout="resume"
  >
    <component
      :is="activeBanner.target_url ? 'a' : 'div'"
      :href="activeBanner.target_url || undefined"
      class="relative block"
    >
      <div
        class="grid place-items-center overflow-hidden bg-[#173b35]"
        :class="compact ? 'aspect-[16/5]' : 'aspect-[16/7] min-h-64'"
      >
        <img
          v-if="!imageFailed"
          :src="activeBanner.image_url"
          :alt="activeBanner.title || 'Banner Mercato'"
          class="h-full w-full object-cover"
          :loading="activeIndex === 0 ? 'eager' : 'lazy'"
          @error="imageFailed = true"
        />
        <PhotoIcon v-else class="h-16 w-16 text-white/50" />
      </div>
      <div
        v-if="activeBanner.title"
        class="pointer-events-none absolute inset-x-0 bottom-0 bg-gradient-to-t from-[#0b2a25]/95 to-transparent px-6 pb-8 pt-20 sm:px-10"
      >
        <p
          class="max-w-3xl font-black tracking-tight"
          :class="compact ? 'text-xl sm:text-3xl' : 'text-2xl sm:text-4xl'"
        >
          {{ activeBanner.title }}
        </p>
      </div>
    </component>

    <template v-if="banners.length > 1">
      <button
        class="absolute left-3 top-1/2 grid h-11 w-11 -translate-y-1/2 place-items-center rounded-full bg-white/90 text-slate-900 shadow-lg hover:bg-white sm:left-5"
        type="button"
        aria-label="Banner trước"
        @click="move(-1)"
      >
        <ChevronLeftIcon class="h-5 w-5" />
      </button>
      <button
        class="absolute right-3 top-1/2 grid h-11 w-11 -translate-y-1/2 place-items-center rounded-full bg-white/90 text-slate-900 shadow-lg hover:bg-white sm:right-5"
        type="button"
        aria-label="Banner tiếp theo"
        @click="move(1)"
      >
        <ChevronRightIcon class="h-5 w-5" />
      </button>
      <div
        class="absolute bottom-3 left-1/2 flex -translate-x-1/2 gap-2 rounded-full bg-slate-950/50 px-3 py-2 backdrop-blur sm:bottom-5"
      >
        <button
          v-for="(banner, index) in banners"
          :key="banner.id"
          class="h-2.5 rounded-full transition-all"
          :class="index === activeIndex ? 'w-7 bg-white' : 'w-2.5 bg-white/50 hover:bg-white/80'"
          type="button"
          :aria-label="`Xem banner ${index + 1}`"
          :aria-current="index === activeIndex ? 'true' : undefined"
          @click="goTo(index)"
        />
      </div>
    </template>
  </section>
</template>
