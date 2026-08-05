<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { getErrorMessage } from '@/features/auth/errors'

import { afterSalesApi } from '../api'
import type { ReviewReport } from '../types'

const reports = ref<ReviewReport[]>([])
const loading = ref(true)
const processingId = ref('')
const error = ref('')
const success = ref('')
const notes = ref<Record<string, string>>({})

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    reports.value = (await afterSalesApi.reviewReports()).data.data
  } catch (requestError) {
    error.value = getErrorMessage(requestError)
  } finally {
    loading.value = false
  }
}

async function resolve(item: ReviewReport, action: 'HIDE' | 'KEEP'): Promise<void> {
  processingId.value = item.id
  error.value = ''
  success.value = ''
  try {
    await afterSalesApi.resolveReviewReport(item.id, action, notes.value[item.id]?.trim() ?? '')
    reports.value = reports.value.filter((report) => report.id !== item.id)
    success.value =
      action === 'HIDE' ? 'Đã ẩn đánh giá vi phạm.' : 'Đã giữ đánh giá và từ chối báo cáo.'
  } catch (requestError) {
    error.value = getErrorMessage(requestError)
  } finally {
    processingId.value = ''
  }
}

onMounted(load)
</script>

<template>
  <main class="mx-auto max-w-5xl space-y-5 px-4 py-8">
    <div>
      <p class="font-bold text-indigo-600">ADM · SEL-15</p>
      <h1 class="text-3xl font-black">Báo cáo đánh giá</h1>
      <p class="mt-2 text-slate-600">
        Kiểm tra nội dung do seller báo cáo trước khi ẩn khỏi trang sản phẩm.
      </p>
    </div>
    <p v-if="error" class="rounded-xl bg-rose-50 p-3 text-rose-700">{{ error }}</p>
    <p v-if="success" class="rounded-xl bg-emerald-50 p-3 text-emerald-700">{{ success }}</p>
    <p v-if="loading" class="rounded-2xl bg-white p-8 text-center text-slate-500">
      Đang tải báo cáo…
    </p>
    <p v-else-if="!reports.length" class="rounded-2xl bg-white p-8 text-center text-slate-500">
      Không có báo cáo đánh giá đang chờ xử lý.
    </p>
    <article v-for="item in reports" :key="item.id" class="rounded-2xl bg-white p-5 shadow-sm">
      <div class="flex flex-wrap justify-between gap-3">
        <div>
          <h2 class="font-black">{{ item.review.product_name }}</h2>
          <p class="text-sm text-slate-500">
            {{ item.review.customer_name }} · {{ item.review.order_code }} ·
            {{ item.reporter_email }}
          </p>
        </div>
        <b class="text-amber-500">{{ '★'.repeat(item.review.rating) }}</b>
      </div>
      <blockquote class="my-3 rounded-xl bg-slate-50 p-3 whitespace-pre-wrap">
        {{ item.review.content || 'Đánh giá không có nội dung.' }}
      </blockquote>
      <div class="rounded-xl bg-rose-50 p-3 text-rose-800">
        <b>{{ item.reason_code }}</b>
        <p class="mt-1 whitespace-pre-wrap">
          {{ item.reason_detail || 'Không có mô tả bổ sung.' }}
        </p>
      </div>
      <label class="mt-4 block text-sm font-bold" :for="`note-${item.id}`">Ghi chú xử lý</label>
      <textarea
        :id="`note-${item.id}`"
        v-model="notes[item.id]"
        class="mt-2 min-h-20 w-full rounded-xl border px-3 py-2"
        maxlength="2000"
        placeholder="Lý do của quyết định…"
      />
      <div class="mt-4 flex flex-wrap gap-2">
        <button
          class="rounded-xl bg-rose-600 px-4 py-2 font-bold text-white disabled:opacity-60"
          :disabled="processingId === item.id"
          type="button"
          @click="resolve(item, 'HIDE')"
        >
          Ẩn đánh giá
        </button>
        <button
          class="rounded-xl border px-4 py-2 font-bold disabled:opacity-60"
          :disabled="processingId === item.id"
          type="button"
          @click="resolve(item, 'KEEP')"
        >
          Giữ đánh giá
        </button>
      </div>
    </article>
  </main>
</template>
