<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { alertDialog, promptDialog } from '@/shared/composables/useAppDialog'

import { afterSalesApi } from '../api'
import type { Review } from '../types'

const reviews = ref<Review[]>([])
const error = ref('')

async function load(): Promise<void> {
  try {
    reviews.value = (await afterSalesApi.sellerReviews()).data.data
  } catch {
    error.value = 'Không thể tải đánh giá.'
  }
}

async function reply(review: Review): Promise<void> {
  const content = await promptDialog({
    title: review.reply ? 'Sửa phản hồi' : 'Phản hồi đánh giá',
    inputLabel: 'Phản hồi công khai',
    initialValue: review.reply?.content ?? '',
    confirmLabel: 'Lưu phản hồi',
    required: true,
  })
  if (!content) return
  await afterSalesApi.replyReview(review.id, content)
  await load()
}

async function report(review: Review): Promise<void> {
  const reason = await promptDialog({
    title: 'Báo cáo đánh giá',
    inputLabel: 'Mô tả nội dung vi phạm',
    confirmLabel: 'Gửi báo cáo',
    destructive: true,
    required: true,
  })
  if (!reason) return
  await afterSalesApi.reportReview(review.id, reason)
  await alertDialog({
    title: 'Đã gửi báo cáo',
    message: 'Báo cáo đã được chuyển đến Admin để xử lý.',
  })
}

onMounted(load)
</script>

<template>
  <main class="mx-auto max-w-5xl space-y-5 px-4 py-8">
    <div>
      <p class="font-bold text-indigo-600">SEL-14 · SEL-15</p>
      <h1 class="text-3xl font-black">Đánh giá của shop</h1>
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
          class="rounded-xl bg-indigo-600 px-4 py-2 font-bold text-white"
          @click="reply(review)"
        >
          {{ review.reply ? 'Sửa phản hồi' : 'Phản hồi' }}</button
        ><button
          class="rounded-xl border border-rose-200 px-4 py-2 font-bold text-rose-700"
          @click="report(review)"
        >
          Báo cáo vi phạm
        </button>
      </div>
    </article>
  </main>
</template>
