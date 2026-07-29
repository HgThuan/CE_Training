<script setup lang="ts">
import { PhotoIcon } from '@heroicons/vue/24/outline'

import type { HomeCategory } from '../types'

defineProps<{ categories: HomeCategory[] }>()
</script>

<template>
  <section>
    <div>
      <p class="text-sm font-bold uppercase tracking-[0.2em] text-indigo-600">Danh mục</p>
      <h2 class="mt-2 text-2xl font-black tracking-tight text-slate-950 sm:text-3xl">
        Khám phá theo nhu cầu
      </h2>
    </div>

    <div v-if="categories.length" class="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
      <RouterLink
        v-for="category in categories"
        :key="category.id"
        :to="{ path: '/products', query: { category: category.id } }"
        class="group overflow-hidden rounded-2xl bg-white text-center shadow-sm ring-1 ring-slate-200 transition hover:-translate-y-1 hover:shadow-lg"
      >
        <div class="grid aspect-square place-items-center overflow-hidden bg-slate-100">
          <img
            v-if="category.image_url"
            :src="category.image_url"
            :alt="category.name"
            class="h-full w-full object-cover transition duration-300 group-hover:scale-105"
            loading="lazy"
          />
          <PhotoIcon v-else class="h-10 w-10 text-slate-400" />
        </div>
        <p class="line-clamp-2 px-3 py-4 text-sm font-bold text-slate-800">{{ category.name }}</p>
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
