<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import FormMessage from '@/features/auth/components/FormMessage.vue'
import { getErrorMessage } from '@/features/auth/errors'

import { sellerApi } from '../api'
import type { Shop, ShopUpdatePayload } from '../types'

const shop = ref<Shop | null>(null)
const form = reactive<ShopUpdatePayload>({})
const loading = ref(true)
const saving = ref(false)
const message = ref('')
const errorMessage = ref('')

async function loadShop(): Promise<void> {
  try {
    shop.value = (await sellerApi.getShop()).data.data
    Object.assign(form, {
      name: shop.value.name,
      description: shop.value.description,
      logo_url: shop.value.logo_url,
      cover_url: shop.value.cover_url,
    })
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
}

async function saveShop(): Promise<void> {
  saving.value = true
  message.value = ''
  errorMessage.value = ''
  try {
    const response = await sellerApi.updateShop({ ...form })
    shop.value = response.data.data
    Object.assign(form, {
      name: shop.value.name,
      description: shop.value.description,
      logo_url: shop.value.logo_url,
      cover_url: shop.value.cover_url,
    })
    message.value = response.data.message
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    saving.value = false
  }
}

onMounted(loadShop)
</script>

<template>
  <main class="mx-auto max-w-4xl px-4 py-10">
    <p class="text-sm font-bold uppercase tracking-[0.2em] text-indigo-600">Seller workspace</p>
    <h1 class="mt-2 text-3xl font-bold">Hồ sơ gian hàng</h1>
    <FormMessage v-if="message" class="mt-6" :message="message" variant="success" />
    <FormMessage v-if="errorMessage" class="mt-6" :message="errorMessage" />
    <p v-if="loading" class="mt-8">Đang tải…</p>
    <form
      v-else-if="shop"
      class="mt-8 grid gap-5 rounded-2xl bg-white p-6 ring-1 ring-gray-200"
      @submit.prevent="saveShop"
    >
      <div
        v-if="shop.status === 'locked'"
        class="rounded-xl bg-red-50 p-4 font-semibold text-red-900"
      >
        Gian hàng đang bị khóa: {{ shop.lock_reason }}
      </div>
      <label class="text-sm font-semibold"
        >Tên gian hàng
        <input v-model.trim="form.name" class="mt-2 w-full rounded-xl border px-3 py-2.5"
      /></label>
      <label class="text-sm font-semibold"
        >Mô tả
        <textarea
          v-model.trim="form.description"
          class="mt-2 min-h-32 w-full rounded-xl border px-3 py-2.5"
        />
      </label>
      <section class="rounded-2xl border p-5">
        <h2 class="font-bold">Logo gian hàng</h2>
        <p class="mt-1 text-sm text-gray-600">
          Nhập URL ảnh công khai. Khuyến nghị ảnh vuông <strong>512 × 512 px</strong>.
        </p>
        <img
          v-if="form.logo_url"
          :src="form.logo_url"
          alt="Xem trước logo gian hàng"
          class="mt-4 size-32 rounded-2xl object-cover ring-1 ring-gray-200"
        />
        <div
          v-else
          class="mt-4 grid size-32 place-items-center rounded-2xl bg-gray-100 text-sm text-gray-500"
        >
          Chưa có logo
        </div>
        <input
          v-model.trim="form.logo_url"
          class="mt-4 block w-full rounded-xl border px-3 py-2.5 text-sm"
          name="logo_url"
          placeholder="https://cdn.example.com/shop/logo.webp"
          type="url"
        />
      </section>

      <section class="rounded-2xl border p-5">
        <h2 class="font-bold">Ảnh bìa gian hàng</h2>
        <p class="mt-1 text-sm text-gray-600">
          Nhập URL ảnh công khai. Khuyến nghị tỷ lệ 10:3, kích thước
          <strong>1600 × 480 px</strong>.
        </p>
        <img
          v-if="form.cover_url"
          :src="form.cover_url"
          alt="Xem trước ảnh bìa gian hàng"
          class="mt-4 aspect-[10/3] w-full rounded-2xl object-cover ring-1 ring-gray-200"
        />
        <div
          v-else
          class="mt-4 grid aspect-[10/3] w-full place-items-center rounded-2xl bg-gray-100 text-sm text-gray-500"
        >
          Chưa có ảnh bìa
        </div>
        <input
          v-model.trim="form.cover_url"
          class="mt-4 block w-full rounded-xl border px-3 py-2.5 text-sm"
          name="cover_url"
          placeholder="https://cdn.example.com/shop/cover.webp"
          type="url"
        />
      </section>
      <div class="flex flex-wrap gap-3">
        <button class="rounded-xl bg-indigo-600 px-5 py-3 font-bold text-white" :disabled="saving">
          Lưu thay đổi
        </button>
        <RouterLink
          class="rounded-xl border px-5 py-3 font-bold"
          :to="{ name: 'public-shop', params: { slug: shop.slug } }"
          target="_blank"
        >
          Xem trang public
        </RouterLink>
      </div>
    </form>
  </main>
</template>
