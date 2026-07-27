<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import FormMessage from '@/features/auth/components/FormMessage.vue'
import { getErrorMessage } from '@/features/auth/errors'

import { shopApi } from '../api'
import type { PublicShopData } from '../types'

const route = useRoute()
const data = ref<PublicShopData | null>(null)
const loading = ref(true)
const errorMessage = ref('')
const sort = ref('newest')

async function loadShop(): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  try {
    data.value = (await shopApi.getPublicShop(String(route.params.slug), 1, sort.value)).data.data
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
}

watch(sort, loadShop)
onMounted(loadShop)
</script>

<template>
  <main class="min-h-screen bg-slate-50">
    <p v-if="loading" class="mx-auto max-w-7xl px-4 py-16">Đang tải gian hàng…</p>
    <div v-else-if="data">
      <div
        class="aspect-[10/3] max-h-[480px] w-full bg-gradient-to-r from-indigo-700 to-violet-600 bg-cover bg-center"
        :style="data.shop.cover_url ? { backgroundImage: `url(${data.shop.cover_url})` } : {}"
      />
      <section class="mx-auto -mt-14 max-w-7xl px-4">
        <div class="flex flex-wrap items-end gap-5 rounded-2xl bg-white p-6 shadow-sm">
          <img
            v-if="data.shop.logo_url"
            :alt="data.shop.name"
            class="size-28 rounded-2xl bg-white object-cover ring-4 ring-white"
            :src="data.shop.logo_url"
          />
          <div class="flex-1">
            <p class="text-sm font-bold uppercase tracking-[0.2em] text-indigo-600">Gian hàng</p>
            <h1 class="mt-1 text-3xl font-bold">{{ data.shop.name }}</h1>
            <p class="mt-2 max-w-3xl text-gray-600">{{ data.shop.description }}</p>
          </div>
          <div class="rounded-xl bg-amber-50 px-4 py-3 text-sm">
            <strong>★ {{ data.shop.average_rating }}</strong
            ><br />
            {{ data.shop.total_products }} sản phẩm
          </div>
        </div>
        <div class="mt-8 flex items-center justify-between">
          <h2 class="text-2xl font-bold">Sản phẩm</h2>
          <select v-model="sort" class="rounded-xl border bg-white px-3 py-2.5">
            <option value="newest">Mới nhất</option>
            <option value="price_asc">Giá tăng dần</option>
            <option value="price_desc">Giá giảm dần</option>
            <option value="rating">Đánh giá cao</option>
          </select>
        </div>
        <div
          v-if="!data.products.length"
          class="mt-6 rounded-2xl border border-dashed bg-white p-12 text-center text-gray-500"
        >
          Sản phẩm sẽ xuất hiện tại đây khi module Product được phát hành trong Sprint 3.
        </div>
      </section>
    </div>
    <FormMessage v-if="errorMessage" class="mx-auto mt-10 max-w-3xl" :message="errorMessage" />
  </main>
</template>
