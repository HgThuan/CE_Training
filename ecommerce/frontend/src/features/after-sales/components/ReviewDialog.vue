<script setup lang="ts">
import { StarIcon as StarIconOutline } from '@heroicons/vue/24/outline'
import { CheckCircleIcon, StarIcon as StarIconSolid, XMarkIcon } from '@heroicons/vue/24/solid'
import { AxiosError } from 'axios'
import { computed, ref, watch } from 'vue'

import { afterSalesApi } from '@/features/after-sales/api'
import type { ReviewMedia } from '@/features/after-sales/types'
import type { OrderItem } from '@/features/order/types'

const props = defineProps<{
  isOpen: boolean
  orderItem: OrderItem | null
}>()

const emit = defineEmits<{
  (event: 'close'): void
  (event: 'submitted'): void
}>()

const rating = ref(0)
const hoverRating = ref(0)
const content = ref('')
const media = ref<ReviewMedia[]>([])
const isSubmitting = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const existingReview = computed(() => props.orderItem?.review)
const isEditMode = computed(() => Boolean(existingReview.value))
const isExpired = computed(() => {
  if (!existingReview.value?.editable_until) return false
  return new Date(existingReview.value.editable_until) < new Date()
})

const ratingLabel = computed(() => {
  const labels = ['', 'Rất không hài lòng', 'Chưa hài lòng', 'Bình thường', 'Hài lòng', 'Rất hài lòng']
  return labels[hoverRating.value || rating.value] || 'Chọn mức độ hài lòng'
})

watch(
  () => props.isOpen,
  (open) => {
    errorMessage.value = ''
    successMessage.value = ''
    hoverRating.value = 0
    if (!open) return
    rating.value = existingReview.value?.rating ?? 0
    content.value = existingReview.value?.content ?? ''
    media.value = [...(existingReview.value?.media ?? [])]
  },
)

function close(): void {
  if (!isSubmitting.value) emit('close')
}

function selectRating(star: number): void {
  if (!isExpired.value && !isSubmitting.value) rating.value = star
}

function apiErrorMessage(error: unknown): string {
  if (!(error instanceof AxiosError)) return 'Đã xảy ra lỗi. Vui lòng thử lại.'
  const response = error.response?.data as { message?: string } | undefined
  return response?.message || 'Không thể lưu đánh giá. Vui lòng thử lại.'
}

async function submitReview(): Promise<void> {
  if (!props.orderItem || isExpired.value) return
  errorMessage.value = ''
  successMessage.value = ''
  if (!rating.value) {
    errorMessage.value = 'Vui lòng chọn số sao trước khi gửi.'
    return
  }

  isSubmitting.value = true
  try {
    const payload = {
      rating: rating.value,
      content: content.value.trim(),
      media: media.value.map((item) => ({
        media_type: item.media_type,
        file_url: item.file_url,
      })),
    }
    if (isEditMode.value && existingReview.value) {
      await afterSalesApi.updateReview(existingReview.value.id, payload)
      successMessage.value = 'Đánh giá đã được cập nhật.'
    } else {
      await afterSalesApi.createReview(props.orderItem.id, payload)
      successMessage.value = 'Cảm ơn bạn đã chia sẻ đánh giá.'
    }
    emit('submitted')
    window.setTimeout(() => emit('close'), 900)
  } catch (error) {
    errorMessage.value = apiErrorMessage(error)
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div v-if="isOpen" class="app-modal" role="presentation" @click.self="close">
    <section
      class="app-modal__panel"
      role="dialog"
      aria-modal="true"
      aria-labelledby="review-dialog-title"
    >
      <div class="flex items-start justify-between gap-4">
        <div>
          <p class="app-page-eyebrow">Mua hàng đã xác thực</p>
          <h2 id="review-dialog-title" class="mt-1 text-xl font-black text-slate-950">
            {{ isEditMode ? 'Cập nhật đánh giá' : 'Đánh giá sản phẩm' }}
          </h2>
        </div>
        <button
          type="button"
          class="workspace-icon-button"
          :disabled="isSubmitting"
          aria-label="Đóng hộp thoại đánh giá"
          @click="close"
        >
          <XMarkIcon class="h-5 w-5" aria-hidden="true" />
        </button>
      </div>

      <div v-if="orderItem" class="mt-5 rounded-xl bg-slate-50 p-4">
        <p class="font-extrabold text-slate-900">{{ orderItem.product_name }}</p>
        <p class="mt-1 text-xs text-slate-500">{{ orderItem.variant_name || orderItem.sku }}</p>
      </div>

      <div v-if="errorMessage" class="workspace-alert workspace-alert--error" role="alert">
        {{ errorMessage }}
      </div>
      <div v-if="successMessage" class="mt-4 flex items-center gap-2 rounded-xl bg-emerald-50 p-4 text-sm font-bold text-emerald-700">
        <CheckCircleIcon class="h-5 w-5" aria-hidden="true" />
        {{ successMessage }}
      </div>

      <form class="mt-6 space-y-5" @submit.prevent="submitReview">
        <fieldset :disabled="isExpired || isSubmitting">
          <legend class="w-full text-center text-sm font-bold text-slate-700">
            Trải nghiệm của bạn thế nào?
          </legend>
          <div class="mt-3 flex justify-center gap-1" @mouseleave="hoverRating = 0">
            <button
              v-for="star in 5"
              :key="star"
              type="button"
              class="rounded-lg p-1.5 transition hover:scale-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 disabled:cursor-not-allowed"
              :aria-label="`${star} sao`"
              :aria-pressed="rating === star"
              @mouseenter="hoverRating = star"
              @focus="hoverRating = star"
              @blur="hoverRating = 0"
              @click="selectRating(star)"
            >
              <StarIconSolid
                v-if="star <= (hoverRating || rating)"
                class="h-9 w-9 text-amber-400"
                aria-hidden="true"
              />
              <StarIconOutline v-else class="h-9 w-9 text-slate-300" aria-hidden="true" />
            </button>
          </div>
          <p class="mt-2 h-5 text-center text-sm font-bold text-amber-700">{{ ratingLabel }}</p>
        </fieldset>

        <label class="block text-sm font-bold text-slate-700">
          Chia sẻ chi tiết <span class="font-normal text-slate-400">(không bắt buộc)</span>
          <textarea
            v-model="content"
            class="mt-2 min-h-28 w-full rounded-xl border border-slate-300 p-3 text-sm leading-6 disabled:bg-slate-50"
            :disabled="isExpired || isSubmitting"
            maxlength="5000"
            placeholder="Chất lượng, kích thước, giao hàng… điều gì hữu ích cho người mua khác?"
          />
          <span class="mt-1 block text-right text-xs font-normal text-slate-400">
            {{ content.length }}/5000
          </span>
        </label>

        <div v-if="media.length" class="space-y-2">
          <p class="text-sm font-bold text-slate-700">Ảnh/video đã đính kèm</p>
          <div class="flex flex-wrap gap-2">
            <div
              v-for="item in media"
              :key="item.id"
              class="h-16 w-16 overflow-hidden rounded-xl border border-slate-200 bg-slate-100"
            >
              <img
                v-if="item.media_type === 'IMAGE'"
                :src="item.file_url"
                alt="Ảnh đánh giá"
                class="h-full w-full object-cover"
              />
              <video v-else :src="item.file_url" class="h-full w-full object-cover" />
            </div>
          </div>
        </div>

        <p v-if="isExpired" class="rounded-xl bg-amber-50 p-4 text-sm text-amber-800">
          Đánh giá đã hết thời hạn chỉnh sửa và hiện ở chế độ chỉ đọc.
        </p>

        <div class="flex gap-3 pt-1">
          <button type="button" class="workspace-page-action flex-1" @click="close">
            {{ isExpired ? 'Đóng' : 'Để sau' }}
          </button>
          <button
            v-if="!isExpired"
            type="submit"
            class="workspace-primary-action flex-1"
            :disabled="isSubmitting"
          >
            {{ isSubmitting ? 'Đang lưu…' : isEditMode ? 'Lưu thay đổi' : 'Gửi đánh giá' }}
          </button>
        </div>
      </form>
    </section>
  </div>
</template>
