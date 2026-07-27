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
const uploading = ref<'logo' | 'cover' | null>(null)
const message = ref('')
const errorMessage = ref('')
const logoFile = ref<File | null>(null)
const coverFile = ref<File | null>(null)
const logoPreview = ref('')
const coverPreview = ref('')

async function loadShop(): Promise<void> {
  try {
    shop.value = (await sellerApi.getShop()).data.data
    Object.assign(form, {
      name: shop.value.name,
      description: shop.value.description,
    })
    logoPreview.value = shop.value.logo_url
    coverPreview.value = shop.value.cover_url
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
}

async function saveShop(): Promise<void> {
  saving.value = true
  try {
    const response = await sellerApi.updateShop({ ...form })
    shop.value = response.data.data
    message.value = response.data.message
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    saving.value = false
  }
}

function selectImage(event: Event, imageType: 'logo' | 'cover'): void {
  const input = event.target as HTMLInputElement
  const selectedFile = input.files?.[0] ?? null
  if (imageType === 'logo') {
    logoFile.value = selectedFile
    logoPreview.value = selectedFile
      ? URL.createObjectURL(selectedFile)
      : (shop.value?.logo_url ?? '')
  } else {
    coverFile.value = selectedFile
    coverPreview.value = selectedFile
      ? URL.createObjectURL(selectedFile)
      : (shop.value?.cover_url ?? '')
  }
}

async function uploadImage(imageType: 'logo' | 'cover'): Promise<void> {
  const image = imageType === 'logo' ? logoFile.value : coverFile.value
  if (!image) return
  uploading.value = imageType
  errorMessage.value = ''
  try {
    const response = await sellerApi.uploadShopImage(imageType, image)
    shop.value = response.data.data
    logoPreview.value = response.data.data.logo_url
    coverPreview.value = response.data.data.cover_url
    if (imageType === 'logo') logoFile.value = null
    else coverFile.value = null
    message.value = response.data.message
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    uploading.value = null
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
          Kích thước cố định: <strong>512 × 512 px</strong>. Ảnh sẽ được crop giữa thành hình vuông
          và chuyển sang WebP.
        </p>
        <img
          v-if="logoPreview"
          :src="logoPreview"
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
          accept="image/jpeg,image/png,image/webp"
          class="mt-4 block w-full text-sm"
          type="file"
          @change="selectImage($event, 'logo')"
        />
        <button
          class="mt-3 rounded-xl bg-gray-950 px-4 py-2.5 font-bold text-white disabled:opacity-50"
          :disabled="!logoFile || uploading !== null"
          type="button"
          @click="uploadImage('logo')"
        >
          {{ uploading === 'logo' ? 'Đang tải logo…' : 'Tải logo lên' }}
        </button>
      </section>

      <section class="rounded-2xl border p-5">
        <h2 class="font-bold">Ảnh bìa gian hàng</h2>
        <p class="mt-1 text-sm text-gray-600">
          Kích thước cố định: <strong>1600 × 480 px</strong>. Ảnh sẽ được crop giữa theo tỷ lệ 10:3
          và chuyển sang WebP.
        </p>
        <img
          v-if="coverPreview"
          :src="coverPreview"
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
          accept="image/jpeg,image/png,image/webp"
          class="mt-4 block w-full text-sm"
          type="file"
          @change="selectImage($event, 'cover')"
        />
        <button
          class="mt-3 rounded-xl bg-gray-950 px-4 py-2.5 font-bold text-white disabled:opacity-50"
          :disabled="!coverFile || uploading !== null"
          type="button"
          @click="uploadImage('cover')"
        >
          {{ uploading === 'cover' ? 'Đang tải ảnh bìa…' : 'Tải ảnh bìa lên' }}
        </button>
      </section>
      <div class="flex flex-wrap gap-3">
        <button class="rounded-xl bg-indigo-600 px-5 py-3 font-bold text-white" :disabled="saving">
          Lưu thay đổi
        </button>
        <RouterLink
          class="rounded-xl border px-5 py-3 font-bold"
          :to="`/shop/${shop.slug}`"
          target="_blank"
        >
          Xem trang public
        </RouterLink>
      </div>
    </form>
  </main>
</template>
