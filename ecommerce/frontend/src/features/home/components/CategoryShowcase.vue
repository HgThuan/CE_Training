<script setup lang="ts">
import {
  ClockIcon,
  ComputerDesktopIcon,
  DevicePhoneMobileIcon,
  DeviceTabletIcon,
  MusicalNoteIcon,
  PuzzlePieceIcon,
  ShoppingBagIcon,
} from '@heroicons/vue/24/outline'
import type { Component } from 'vue'
import { ref } from 'vue'

import type { HomeCategory } from '../types'

defineProps<{ categories: HomeCategory[] }>()
const failedImages = ref(new Set<string>())

function categoryIcon(name: string): Component {
  const normalized = name.toLocaleLowerCase('vi')
  if (normalized.includes('âm thanh')) return MusicalNoteIcon
  if (normalized.includes('laptop')) return ComputerDesktopIcon
  if (normalized.includes('đeo')) return ClockIcon
  if (normalized.includes('điện thoại')) return DevicePhoneMobileIcon
  if (normalized.includes('máy tính bảng')) return DeviceTabletIcon
  if (normalized.includes('phụ kiện')) return PuzzlePieceIcon
  return ShoppingBagIcon
}
</script>

<template>
  <section>
    <div>
      <h2 class="text-2xl font-black tracking-tight text-[#0b2a25] sm:text-3xl">
        Khám phá theo nhu cầu
      </h2>
    </div>

    <div v-if="categories.length" class="mt-5 flex gap-3 overflow-x-auto pb-2">
      <RouterLink
        v-for="category in categories"
        :key="category.id"
        :to="{ path: '/products', query: { category: category.id } }"
        class="group flex min-w-44 items-center gap-3 overflow-hidden rounded-xl bg-[#fffdf8] p-2 text-left shadow-[0_8px_24px_rgba(23,59,53,0.07)] transition hover:-translate-y-1 hover:shadow-[0_12px_30px_rgba(23,59,53,0.12)]"
      >
        <div
          class="grid size-14 shrink-0 place-items-center overflow-hidden rounded-lg bg-slate-100"
        >
          <img
            v-if="category.image_url && !failedImages.has(category.id)"
            :src="category.image_url"
            :alt="category.name"
            class="h-full w-full object-cover transition duration-300 group-hover:scale-105"
            loading="lazy"
            decoding="async"
            @error="failedImages = new Set(failedImages).add(category.id)"
          />
          <div
            v-else
            class="grid h-full w-full place-items-center bg-[#e8eee9] text-[#173b35]"
            role="img"
            :aria-label="`Chưa có ảnh danh mục ${category.name}`"
          >
            <span class="grid size-10 place-items-center rounded-lg bg-[#fffdf8] shadow-sm">
              <component :is="categoryIcon(category.name)" class="size-5" aria-hidden="true" />
            </span>
          </div>
        </div>
        <p class="line-clamp-2 pr-2 text-sm font-bold text-[#173b35]">{{ category.name }}</p>
      </RouterLink>
    </div>

    <p
      v-else
      class="mt-6 rounded-3xl border border-dashed border-slate-300 bg-white px-6 py-10 text-center text-sm text-slate-600"
    >
      Danh mục nổi bật đang được cập nhật.
    </p>
  </section>
</template>
