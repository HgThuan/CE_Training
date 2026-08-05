<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { getErrorMessage } from '@/features/auth/errors'

import { afterSalesApi } from '../api'
import type { Review } from '../types'

const props = defineProps<{
  open: boolean
  orderItemId: string
  productName: string
  review: Review | null
}>()
const emit = defineEmits<{
  close: []
  saved: [review: Review]
}>()

const rating = ref(5)
const content = ref('')
const mediaUrls = ref('')
const submitting = ref(false)
const error = ref('')
const title = computed(() => (props.review ? 'Sửa đánh giá' : 'Đánh giá sản phẩm'))

watch(
  () => [props.open, props.review] as const,
  ([open, review]) => {
    if (!open) return
    rating.value = review?.rating ?? 5
    content.value = review?.content ?? ''
    mediaUrls.value = review?.media.map((item) => item.file_url).join('\n') ?? ''
    error.value = ''
  },
  { immediate: true },
)

function mediaType(url: string): 'IMAGE' | 'VIDEO' {
  return /\.(mp4|webm|mov)(?:\?|$)/i.test(url) ? 'VIDEO' : 'IMAGE'
}

async function submit(): Promise<void> {
  const urls = mediaUrls.value
    .split('\n')
    .map((url) => url.trim())
    .filter(Boolean)
  const media = urls.map((file_url) => ({ media_type: mediaType(file_url), file_url }))
  if (media.filter((item) => item.media_type === 'IMAGE').length > 5) {
    error.value = 'Mỗi đánh giá chỉ được tối đa 5 ảnh.'
    return
  }
  if (media.filter((item) => item.media_type === 'VIDEO').length > 1) {
    error.value = 'Mỗi đánh giá chỉ được tối đa 1 video.'
    return
  }

  submitting.value = true
  error.value = ''
  try {
    const payload = { rating: rating.value, content: content.value.trim(), media }
    const response = props.review
      ? await afterSalesApi.updateReview(props.review.id, payload)
      : await afterSalesApi.createReview(props.orderItemId, payload)
    emit('saved', response.data.data)
    emit('close')
  } catch (requestError) {
    error.value = getErrorMessage(requestError)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-slate-950/60 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="review-dialog-title"
      @click.self="emit('close')"
    >
      <form class="w-full max-w-lg rounded-3xl bg-white p-6 shadow-2xl" @submit.prevent="submit">
        <div class="flex items-start justify-between gap-4">
          <div>
            <h2 id="review-dialog-title" class="text-2xl font-black">{{ title }}</h2>
            <p class="mt-1 text-sm text-slate-500">{{ productName }}</p>
          </div>
          <button
            class="rounded-lg px-2 py-1 text-xl text-slate-500"
            type="button"
            @click="emit('close')"
          >
            ×
          </button>
        </div>

        <fieldset class="mt-6">
          <legend class="text-sm font-bold text-slate-700">Mức độ hài lòng</legend>
          <div class="mt-2 flex gap-2">
            <button
              v-for="star in 5"
              :key="star"
              class="text-3xl transition hover:scale-110"
              :class="star <= rating ? 'text-amber-400' : 'text-slate-300'"
              type="button"
              :aria-label="`${star} sao`"
              @click="rating = star"
            >
              ★
            </button>
          </div>
        </fieldset>

        <label class="mt-5 block text-sm font-bold text-slate-700" for="review-content">
          Nội dung đánh giá
        </label>
        <textarea
          id="review-content"
          v-model="content"
          class="mt-2 min-h-28 w-full rounded-xl border border-slate-300 px-4 py-3"
          maxlength="5000"
          placeholder="Chia sẻ trải nghiệm thực tế của bạn…"
        />

        <label class="mt-4 block text-sm font-bold text-slate-700" for="review-media">
          URL ảnh/video (mỗi dòng một URL)
        </label>
        <textarea
          id="review-media"
          v-model="mediaUrls"
          class="mt-2 min-h-20 w-full rounded-xl border border-slate-300 px-4 py-3 text-sm"
          placeholder="https://example.com/anh.webp"
        />
        <p class="mt-1 text-xs text-slate-500">Tối đa 5 ảnh và 1 video.</p>

        <p v-if="error" class="mt-4 rounded-xl bg-rose-50 p-3 text-sm text-rose-700">{{ error }}</p>
        <div class="mt-6 flex justify-end gap-3">
          <button
            class="rounded-xl border px-4 py-2 font-bold"
            type="button"
            @click="emit('close')"
          >
            Hủy
          </button>
          <button
            class="rounded-xl bg-indigo-600 px-5 py-2 font-bold text-white disabled:opacity-60"
            :disabled="submitting"
            type="submit"
          >
            {{ submitting ? 'Đang lưu…' : props.review ? 'Lưu thay đổi' : 'Gửi đánh giá' }}
          </button>
        </div>
      </form>
    </div>
  </Teleport>
</template>
