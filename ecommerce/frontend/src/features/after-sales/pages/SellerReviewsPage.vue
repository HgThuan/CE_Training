<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { getErrorMessage } from '@/features/auth/errors'

import { afterSalesApi } from '../api'
import type { Review } from '../types'

const reviews = ref<Review[]>([])
const loading = ref(true)
const actionId = ref('')
const error = ref('')
const success = ref('')
const rating = ref('')
const status = ref('')
const replyDrafts = ref<Record<string, string>>({})
const reportDrafts = ref<Record<string, string>>({})
const reportedIds = ref(new Set<string>())

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const params: Record<string, string> = {}
    if (rating.value) params.rating = rating.value
    if (status.value) params.status = status.value
    reviews.value = (await afterSalesApi.sellerReviews(params)).data.data
    replyDrafts.value = Object.fromEntries(
      reviews.value.map((review) => [review.id, review.reply?.content ?? '']),
    )
  } catch (requestError) {
    error.value = getErrorMessage(requestError)
  } finally {
    loading.value = false
  }
}

async function reply(review: Review): Promise<void> {
  const content = replyDrafts.value[review.id]?.trim()
  if (!content) {
    error.value = 'Vui lòng nhập nội dung phản hồi.'
    return
  }
  actionId.value = review.id
  error.value = ''
  success.value = ''
  try {
    const response = await afterSalesApi.replyReview(review.id, content)
    Object.assign(review, response.data.data)
    success.value = 'Đã lưu phản hồi công khai.'
  } catch (requestError) {
    error.value = getErrorMessage(requestError)
  } finally {
    actionId.value = ''
  }
}

async function report(review: Review): Promise<void> {
  const reason = reportDrafts.value[review.id]?.trim()
  if (!reason) {
    error.value = 'Vui lòng mô tả nội dung vi phạm.'
    return
  }
  actionId.value = review.id
  error.value = ''
  success.value = ''
  try {
    await afterSalesApi.reportReview(review.id, reason)
    reportedIds.value = new Set(reportedIds.value).add(review.id)
    success.value = 'Đã chuyển báo cáo đến Admin.'
  } catch (requestError) {
    error.value = getErrorMessage(requestError)
  } finally {
    actionId.value = ''
  }
}

onMounted(load)
</script>

<template>
  <main class="mx-auto max-w-5xl space-y-5 px-4 py-8">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div>
        <p class="font-bold text-indigo-600">SEL-14 · SEL-15</p>
        <h1 class="text-3xl font-black">Đánh giá của shop</h1>
      </div>
      <div class="flex gap-2">
        <select
          v-model="rating"
          class="rounded-xl border px-3 py-2"
          aria-label="Lọc số sao"
          @change="load"
        >
          <option value="">Tất cả số sao</option>
          <option v-for="star in 5" :key="star" :value="String(star)">{{ star }} sao</option>
        </select>
        <select
          v-model="status"
          class="rounded-xl border px-3 py-2"
          aria-label="Lọc trạng thái"
          @change="load"
        >
          <option value="">Tất cả trạng thái</option>
          <option value="VISIBLE">Đang hiển thị</option>
          <option value="HIDDEN">Đã ẩn</option>
          <option value="PENDING_MODERATION">Chờ kiểm duyệt</option>
        </select>
      </div>
    </div>

    <p v-if="error" class="rounded-xl bg-rose-50 p-3 text-rose-700">{{ error }}</p>
    <p v-if="success" class="rounded-xl bg-emerald-50 p-3 text-emerald-700">{{ success }}</p>
    <p v-if="loading" class="rounded-2xl bg-white p-8 text-center text-slate-500">
      Đang tải đánh giá…
    </p>
    <p v-else-if="!reviews.length" class="rounded-2xl bg-white p-8 text-center text-slate-500">
      Chưa có đánh giá phù hợp.
    </p>

    <article v-for="review in reviews" :key="review.id" class="rounded-2xl bg-white p-5 shadow-sm">
      <div class="flex justify-between gap-4">
        <div>
          <h2 class="font-black">{{ review.product_name }}</h2>
          <p class="text-sm text-slate-500">{{ review.customer_name }} · {{ review.order_code }}</p>
          <span class="mt-2 inline-block rounded-full bg-slate-100 px-2 py-1 text-xs font-bold">
            {{ review.status }}
          </span>
        </div>
        <b class="text-amber-500">{{ '★'.repeat(review.rating) }}</b>
      </div>
      <p class="my-4 whitespace-pre-wrap">
        {{ review.content || 'Khách hàng không để lại bình luận.' }}
      </p>
      <div v-if="review.media.length" class="mb-4 flex flex-wrap gap-2">
        <a
          v-for="media in review.media"
          :key="media.id"
          class="rounded-lg border px-3 py-2 text-sm font-bold text-indigo-700"
          :href="media.file_url"
          target="_blank"
          rel="noopener noreferrer"
        >
          {{ media.media_type === 'IMAGE' ? 'Xem ảnh' : 'Xem video' }}
        </a>
      </div>

      <div class="grid gap-4 border-t pt-4 md:grid-cols-2">
        <form @submit.prevent="reply(review)">
          <label class="text-sm font-bold" :for="`reply-${review.id}`">Phản hồi công khai</label>
          <textarea
            :id="`reply-${review.id}`"
            v-model="replyDrafts[review.id]"
            class="mt-2 min-h-20 w-full rounded-xl border px-3 py-2"
            maxlength="5000"
            placeholder="Nhập phản hồi của shop…"
          />
          <button
            class="mt-2 rounded-xl bg-indigo-600 px-4 py-2 font-bold text-white disabled:opacity-60"
            :disabled="actionId === review.id"
            type="submit"
          >
            {{ review.reply ? 'Cập nhật phản hồi' : 'Gửi phản hồi' }}
          </button>
        </form>

        <form @submit.prevent="report(review)">
          <label class="text-sm font-bold" :for="`report-${review.id}`">Báo cáo vi phạm</label>
          <textarea
            :id="`report-${review.id}`"
            v-model="reportDrafts[review.id]"
            class="mt-2 min-h-20 w-full rounded-xl border px-3 py-2"
            maxlength="2000"
            placeholder="Mô tả lý do cần Admin kiểm tra…"
          />
          <button
            class="mt-2 rounded-xl border border-rose-200 px-4 py-2 font-bold text-rose-700 disabled:opacity-60"
            :disabled="actionId === review.id || reportedIds.has(review.id)"
            type="submit"
          >
            {{ reportedIds.has(review.id) ? 'Đã báo cáo' : 'Gửi báo cáo' }}
          </button>
        </form>
      </div>
    </article>
  </main>
</template>
