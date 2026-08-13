<script setup lang="ts">
import { ArrowLeftIcon, PhotoIcon } from '@heroicons/vue/24/outline'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import FormMessage from '@/features/auth/components/FormMessage.vue'
import { getErrorMessage } from '@/features/auth/errors'

import { adminBannersApi } from '../api'
import type { Banner, BannerPayload, BannerPosition } from '../types'

const route = useRoute()
const router = useRouter()
const bannerId = computed(() =>
  typeof route.params.bannerId === 'string' ? route.params.bannerId : '',
)
const isEditing = computed(() => Boolean(bannerId.value))
const loading = ref(isEditing.value)
const saving = ref(false)
const imageFailed = ref(false)
const errorMessage = ref('')

const form = reactive({
  title: '',
  imageUrl: '',
  targetUrl: '',
  position: 'hero' as BannerPosition,
  sortOrder: 0,
  startsAt: '',
  endsAt: '',
  isActive: true,
})

const positionOptions: Array<{ value: BannerPosition; label: string }> = [
  { value: 'hero', label: 'Đầu trang' },
  { value: 'middle', label: 'Giữa trang' },
]

watch(
  () => form.imageUrl,
  () => {
    imageFailed.value = false
  },
)

function toLocalDateTime(value: string | null): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const pad = (part: number): string => String(part).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(
    date.getHours(),
  )}:${pad(date.getMinutes())}`
}

function hydrateForm(banner: Banner): void {
  Object.assign(form, {
    title: banner.title ?? '',
    imageUrl: banner.image_url,
    targetUrl: banner.target_url ?? '',
    position: banner.position,
    sortOrder: banner.sort_order,
    startsAt: toLocalDateTime(banner.starts_at),
    endsAt: toLocalDateTime(banner.ends_at),
    isActive: banner.is_active,
  })
}

function toIsoDateTime(value: string): string | null {
  return value ? new Date(value).toISOString() : null
}

function validateForm(): string | null {
  if (form.startsAt && form.endsAt && new Date(form.startsAt) >= new Date(form.endsAt)) {
    return 'Thời gian kết thúc phải sau thời gian bắt đầu.'
  }
  if (!form.title.trim()) return 'Vui lòng nhập tiêu đề để nhận diện banner.'
  if (!form.imageUrl.trim()) return 'Vui lòng nhập URL ảnh banner.'
  try {
    const imageUrl = new URL(form.imageUrl)
    if (!['http:', 'https:'].includes(imageUrl.protocol)) throw new Error()
  } catch {
    return 'URL ảnh phải là liên kết HTTP hoặc HTTPS hợp lệ.'
  }
  if (imageFailed.value) return 'Ảnh không tải được. Hãy kiểm tra lại URL trước khi lưu.'
  if (form.targetUrl.trim()) {
    try {
      const targetUrl = new URL(form.targetUrl)
      if (!['http:', 'https:'].includes(targetUrl.protocol)) throw new Error()
    } catch {
      return 'Liên kết đích phải là URL HTTP hoặc HTTPS hợp lệ.'
    }
  }
  if (form.sortOrder < 0 || !Number.isInteger(form.sortOrder)) {
    return 'Thứ tự phải là số nguyên không âm.'
  }
  return null
}

async function loadBanner(): Promise<void> {
  if (!bannerId.value) return
  loading.value = true
  errorMessage.value = ''
  try {
    hydrateForm((await adminBannersApi.detail(bannerId.value)).data.data)
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
}

async function saveBanner(): Promise<void> {
  const validationError = validateForm()
  if (validationError) {
    errorMessage.value = validationError
    return
  }

  saving.value = true
  errorMessage.value = ''
  const payload: BannerPayload = {
    title: form.title.trim() || null,
    image_url: form.imageUrl.trim(),
    target_url: form.targetUrl.trim() || null,
    position: form.position,
    sort_order: form.sortOrder,
    starts_at: toIsoDateTime(form.startsAt),
    ends_at: toIsoDateTime(form.endsAt),
    is_active: form.isActive,
  }
  try {
    if (bannerId.value) {
      await adminBannersApi.update(bannerId.value, payload)
    } else {
      await adminBannersApi.create(payload)
    }
    await router.push({
      path: '/admin/banners',
      query: { saved: isEditing.value ? 'updated' : 'created' },
    })
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    saving.value = false
  }
}

onMounted(loadBanner)
</script>

<template>
  <main class="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:py-10">
    <RouterLink
      class="inline-flex items-center gap-2 text-sm font-bold text-slate-600 hover:text-indigo-700"
      to="/admin/banners"
    >
      <ArrowLeftIcon class="h-4 w-4" />
      Quay lại danh sách
    </RouterLink>

    <div class="mt-6">
      <h1 class="mt-2 text-3xl font-black tracking-tight sm:text-4xl">
        {{ isEditing ? 'Cập nhật banner' : 'Tạo banner mới' }}
      </h1>
      <p class="mt-3 text-slate-600">
        Dùng URL ảnh công khai và đặt khoảng thời gian hiển thị nếu cần.
      </p>
    </div>

    <FormMessage v-if="errorMessage" class="mt-6" :message="errorMessage" />

    <div
      v-if="loading"
      class="mt-8 grid animate-pulse gap-8 rounded-3xl bg-white p-6 ring-1 ring-slate-200 lg:grid-cols-2 lg:p-8"
    >
      <div class="aspect-[16/9] rounded-2xl bg-slate-200" />
      <div class="space-y-5">
        <div v-for="index in 5" :key="index" class="h-12 rounded-xl bg-slate-100" />
      </div>
    </div>

    <form
      v-else
      class="mt-8 grid gap-8 rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200 lg:grid-cols-[0.9fr_1.1fr] lg:p-8"
      @submit.prevent="saveBanner"
    >
      <section>
        <h2 class="text-lg font-black">Xem trước</h2>
        <div
          class="mt-4 grid aspect-[16/9] place-items-center overflow-hidden rounded-2xl bg-slate-100 ring-1 ring-slate-200"
        >
          <img
            v-if="form.imageUrl && !imageFailed"
            :src="form.imageUrl"
            :alt="form.title || 'Xem trước banner'"
            class="h-full w-full object-cover"
            @error="imageFailed = true"
          />
          <div v-else class="grid place-items-center gap-3 px-6 text-center text-slate-400">
            <PhotoIcon class="h-12 w-12" />
            <p class="text-sm font-semibold">
              {{ imageFailed ? 'Không thể tải ảnh từ URL này.' : 'Nhập URL để xem trước banner.' }}
            </p>
          </div>
        </div>
        <div class="mt-4 rounded-2xl bg-slate-50 p-4 text-sm text-slate-600">
          <p class="font-bold text-slate-900">{{ form.title || 'Nhập tiêu đề banner' }}</p>
          <p class="mt-1 break-all">{{ form.targetUrl || 'Không có liên kết đích' }}</p>
        </div>
      </section>

      <section class="grid content-start gap-5 sm:grid-cols-2">
        <label class="sm:col-span-2">
          <span class="text-sm font-bold">Tiêu đề *</span>
          <input
            v-model.trim="form.title"
            class="mt-2 w-full rounded-xl border border-slate-300 px-3 py-3"
            maxlength="180"
            required
          />
        </label>

        <label class="sm:col-span-2">
          <span class="text-sm font-bold">URL ảnh *</span>
          <input
            v-model.trim="form.imageUrl"
            class="mt-2 w-full rounded-xl border border-slate-300 px-3 py-3"
            type="url"
            inputmode="url"
            required
            placeholder="https://..."
          />
        </label>

        <label class="sm:col-span-2">
          <span class="text-sm font-bold">Liên kết đích</span>
          <input
            v-model.trim="form.targetUrl"
            class="mt-2 w-full rounded-xl border border-slate-300 px-3 py-3"
            type="url"
            inputmode="url"
            placeholder="https://..."
          />
        </label>

        <label>
          <span class="text-sm font-bold">Vị trí *</span>
          <select
            v-model="form.position"
            class="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-3"
            required
          >
            <option v-for="option in positionOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>

        <p class="rounded-xl bg-indigo-50 px-3 py-2 text-sm text-indigo-800 sm:col-span-2">
          Kích thước gợi ý:
          {{
            form.position === 'hero' ? '1600 × 700 px (tỷ lệ 16:7)' : '1600 × 600 px (tỷ lệ 8:3)'
          }}. Ảnh nên dưới 2 MB để tải nhanh.
        </p>

        <label v-if="isEditing">
          <span class="text-sm font-bold">Thứ tự *</span>
          <input
            v-model.number="form.sortOrder"
            class="mt-2 w-full rounded-xl border border-slate-300 px-3 py-3"
            type="number"
            min="0"
            step="1"
            required
          />
        </label>

        <label>
          <span class="text-sm font-bold">Bắt đầu hiển thị</span>
          <input
            v-model="form.startsAt"
            class="mt-2 w-full rounded-xl border border-slate-300 px-3 py-3"
            type="datetime-local"
          />
        </label>

        <label>
          <span class="text-sm font-bold">Kết thúc hiển thị</span>
          <input
            v-model="form.endsAt"
            class="mt-2 w-full rounded-xl border border-slate-300 px-3 py-3"
            type="datetime-local"
          />
        </label>

        <label class="flex items-center gap-3 text-sm font-bold sm:col-span-2">
          <input v-model="form.isActive" class="h-5 w-5 accent-indigo-600" type="checkbox" />
          Cho phép banner hiển thị
        </label>

        <div class="flex flex-wrap justify-end gap-3 border-t border-slate-200 pt-5 sm:col-span-2">
          <RouterLink
            class="rounded-xl border border-slate-300 px-5 py-3 font-bold text-slate-700"
            to="/admin/banners"
          >
            Hủy
          </RouterLink>
          <button
            class="rounded-xl bg-indigo-600 px-5 py-3 font-bold text-white disabled:opacity-50"
            type="submit"
            :disabled="saving"
          >
            {{ saving ? 'Đang lưu…' : isEditing ? 'Lưu thay đổi' : 'Tạo banner' }}
          </button>
        </div>
      </section>
    </form>
  </main>
</template>
