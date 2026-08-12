<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { afterSalesApi } from '../api'
import type { Review } from '../types'
import InputDialog from '@/shared/components/InputDialog.vue'

const reviews = ref<Review[]>([])
const error = ref('')
const successMessage = ref('')

const isReplyDialogOpen = ref(false)
const selectedReviewForReply = ref<Review | null>(null)

const isReportDialogOpen = ref(false)
const selectedReviewForReport = ref<Review | null>(null)

async function load(): Promise<void> {
  try {
    reviews.value = (await afterSalesApi.sellerReviews()).data.data
  } catch {
    error.value = 'Không thể tải đánh giá.'
  }
}

function openReplyDialog(review: Review) {
  selectedReviewForReply.value = review
  isReplyDialogOpen.value = true
}

async function handleReplyConfirm(content: string) {
  if (!content.trim() || !selectedReviewForReply.value) return
  isReplyDialogOpen.value = false

  await afterSalesApi.replyReview(selectedReviewForReply.value.id, content)
  successMessage.value = 'Đã phản hồi thành công.'
  setTimeout(() => {
    successMessage.value = ''
  }, 3000)
  selectedReviewForReply.value = null
  await load()
}

function openReportDialog(review: Review) {
  selectedReviewForReport.value = review
  isReportDialogOpen.value = true
}

async function handleReportConfirm(reason: string) {
  if (!reason.trim() || !selectedReviewForReport.value) return
  isReportDialogOpen.value = false

  await afterSalesApi.reportReview(selectedReviewForReport.value.id, reason)
  successMessage.value = 'Đã chuyển báo cáo đến Admin thành công.'
  setTimeout(() => {
    successMessage.value = ''
  }, 3000)
  selectedReviewForReport.value = null
}

onMounted(load)
</script>

<template>
  <main class="mx-auto max-w-5xl space-y-5 px-4 py-8">
    <div>
      <p class="font-bold text-indigo-600">SEL-14 · SEL-15</p>
      <h1 class="text-3xl font-black">Đánh giá của shop</h1>
    </div>

    <div v-if="successMessage" class="rounded-md bg-emerald-50 p-3 text-sm text-emerald-700">
      {{ successMessage }}
    </div>
    <p v-if="error" class="text-rose-700">{{ error }}</p>

    <article v-for="review in reviews" :key="review.id" class="rounded-2xl bg-white p-5 shadow-sm">
      <div class="flex justify-between gap-4">
        <div>
          <h2 class="font-black">{{ review.product_name }}</h2>
          <p class="text-sm text-slate-500">{{ review.customer_name }} · {{ review.order_code }}</p>
        </div>
        <b class="text-amber-500">{{ '★'.repeat(review.rating) }}</b>
      </div>
      <p class="my-4">{{ review.content || 'Khách hàng không để lại bình luận.' }}</p>
      <blockquote v-if="review.reply" class="rounded-xl bg-indigo-50 p-4 text-sm">
        <b>Phản hồi của shop:</b> {{ review.reply.content }}
      </blockquote>
      <div class="mt-4 flex gap-2">
        <button
          class="rounded-xl bg-indigo-600 px-4 py-2 font-bold text-white hover:bg-indigo-700"
          @click="openReplyDialog(review)"
        >
          {{ review.reply ? 'Sửa phản hồi' : 'Phản hồi' }}
        </button>
        <button
          class="rounded-xl border border-rose-200 bg-rose-50 px-4 py-2 font-bold text-rose-700 hover:bg-rose-100"
          @click="openReportDialog(review)"
        >
          Báo cáo vi phạm
        </button>
      </div>
    </article>

    <InputDialog
      :is-open="isReplyDialogOpen"
      title="Phản hồi công khai"
      placeholder="Nhập nội dung phản hồi đánh giá của khách hàng..."
      confirm-text="Gửi phản hồi"
      :initial-value="selectedReviewForReply?.reply?.content"
      :multiline="true"
      @close="isReplyDialogOpen = false"
      @confirm="handleReplyConfirm"
    />

    <InputDialog
      :is-open="isReportDialogOpen"
      title="Báo cáo vi phạm"
      placeholder="Mô tả nội dung vi phạm..."
      confirm-text="Gửi báo cáo"
      :multiline="true"
      @close="isReportDialogOpen = false"
      @confirm="handleReportConfirm"
    />
  </main>
</template>
