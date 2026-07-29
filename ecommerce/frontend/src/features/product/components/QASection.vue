<script setup lang="ts">
import {
  ChatBubbleLeftRightIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  UserCircleIcon,
} from '@heroicons/vue/24/outline'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import FormMessage from '@/features/auth/components/FormMessage.vue'
import { getErrorMessage } from '@/features/auth/errors'
import type { PaginationMeta } from '@/shared/types/api'
import { useAuthStore } from '@/stores/auth'

import { productApi } from '../api'
import type { ProductQuestion } from '../types'

const props = defineProps<{ productId: string }>()

const route = useRoute()
const authStore = useAuthStore()
const questions = ref<ProductQuestion[]>([])
const meta = ref<PaginationMeta>({
  page: 1,
  page_size: 10,
  total_items: 0,
  total_pages: 0,
})
const loading = ref(true)
const submitting = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const content = ref('')
let requestSequence = 0

const canAsk = computed(() => authStore.user?.role === 'customer')
const loginLocation = computed(() => {
  const pathWithoutHash = route.fullPath.split('#')[0] || '/'
  return {
    path: '/auth/login',
    query: { redirect: `${pathWithoutHash}#qa` },
  }
})

function displayName(name: string, fallback: string): string {
  return name.trim() || fallback
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('vi-VN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

async function loadQuestions(page = 1): Promise<void> {
  const sequence = ++requestSequence
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await productApi.listQuestions(props.productId, {
      page,
      page_size: 10,
    })
    if (sequence !== requestSequence) return
    questions.value = response.data.data
    meta.value =
      response.data.meta ??
      ({
        page,
        page_size: 10,
        total_items: questions.value.length,
        total_pages: questions.value.length ? 1 : 0,
      } satisfies PaginationMeta)
  } catch (error) {
    if (sequence === requestSequence) errorMessage.value = getErrorMessage(error)
  } finally {
    if (sequence === requestSequence) loading.value = false
  }
}

async function submitQuestion(): Promise<void> {
  const normalized = content.value.trim()
  if (normalized.length < 3 || submitting.value) return
  submitting.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    const response = await productApi.createQuestion(props.productId, {
      content: normalized,
    })
    content.value = ''
    successMessage.value = response.data.message
    await loadQuestions(1)
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    submitting.value = false
  }
}

watch(
  () => props.productId,
  () => {
    questions.value = []
    successMessage.value = ''
    void loadQuestions(1)
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  requestSequence += 1
})
</script>

<template>
  <section aria-labelledby="qa-heading">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 id="qa-heading" class="text-2xl font-black">Hỏi đáp về sản phẩm</h2>
        <p class="mt-1 text-sm text-slate-500">{{ meta.total_items }} câu hỏi đang hiển thị</p>
      </div>
      <ChatBubbleLeftRightIcon class="h-8 w-8 text-indigo-600" aria-hidden="true" />
    </div>

    <FormMessage v-if="errorMessage" class="mt-5" :message="errorMessage" />
    <p
      v-if="successMessage"
      class="mt-5 rounded-xl bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-800"
      role="status"
    >
      {{ successMessage }}
    </p>

    <form
      v-if="canAsk"
      class="mt-6 rounded-2xl bg-slate-50 p-4 sm:p-5"
      @submit.prevent="submitQuestion"
    >
      <label class="block text-sm font-bold text-slate-800">
        Câu hỏi của bạn
        <textarea
          v-model="content"
          class="mt-2 min-h-28 w-full resize-y rounded-xl border border-slate-300 bg-white px-4 py-3 font-normal outline-none focus:border-indigo-600 focus:ring-4 focus:ring-indigo-100"
          minlength="3"
          maxlength="2000"
          required
          placeholder="Ví dụ: Sản phẩm được bảo hành trong bao lâu?"
        />
      </label>
      <div class="mt-3 flex items-center justify-between gap-3">
        <span class="text-xs text-slate-500">{{ content.length }}/2000</span>
        <button
          class="rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-bold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
          :disabled="submitting || content.trim().length < 3"
        >
          {{ submitting ? 'Đang gửi…' : 'Gửi câu hỏi' }}
        </button>
      </div>
    </form>

    <div
      v-else-if="!authStore.user"
      class="mt-6 rounded-2xl border border-indigo-200 bg-indigo-50 p-5 text-sm text-indigo-950"
    >
      <p class="font-semibold">Đăng nhập bằng tài khoản Customer để đặt câu hỏi.</p>
      <RouterLink
        class="mt-3 inline-flex rounded-xl bg-indigo-600 px-4 py-2 font-bold text-white"
        :to="loginLocation"
      >
        Đăng nhập để hỏi
      </RouterLink>
    </div>

    <p v-else class="mt-6 rounded-2xl bg-slate-100 p-5 text-sm font-semibold text-slate-600">
      Chỉ tài khoản Customer có thể đặt câu hỏi. Bạn vẫn có thể xem toàn bộ câu trả lời công khai.
    </p>

    <div v-if="loading" class="mt-8 space-y-4" aria-label="Đang tải hỏi đáp">
      <div v-for="index in 3" :key="index" class="animate-pulse rounded-2xl bg-slate-100 p-5">
        <div class="h-4 w-1/3 rounded bg-slate-200" />
        <div class="mt-4 h-5 rounded bg-slate-200" />
        <div class="mt-3 h-16 rounded bg-slate-200" />
      </div>
    </div>

    <div v-else-if="questions.length" class="mt-8 space-y-5" aria-live="polite">
      <article
        v-for="question in questions"
        :key="question.id"
        class="rounded-2xl border border-slate-200 p-5"
      >
        <div class="flex items-start gap-3">
          <img
            v-if="question.customer.avatar_url"
            class="h-10 w-10 rounded-full object-cover"
            :src="question.customer.avatar_url"
            :alt="displayName(question.customer.full_name, 'Khách hàng')"
            loading="lazy"
            decoding="async"
          />
          <UserCircleIcon v-else class="h-10 w-10 text-slate-400" aria-hidden="true" />
          <div class="min-w-0">
            <p class="font-bold text-slate-900">
              {{ displayName(question.customer.full_name, 'Khách hàng') }}
            </p>
            <time class="text-xs text-slate-500" :datetime="question.created_at">
              {{ formatDate(question.created_at) }}
            </time>
          </div>
        </div>
        <p class="mt-4 whitespace-pre-line leading-7 text-slate-800">{{ question.content }}</p>

        <div
          v-if="question.answer"
          class="mt-5 rounded-2xl border-l-4 border-indigo-500 bg-indigo-50 p-4"
        >
          <p class="text-xs font-bold uppercase tracking-wider text-indigo-700">
            {{ displayName(question.answer.seller.full_name, 'Nhà bán') }} trả lời
          </p>
          <p class="mt-2 whitespace-pre-line leading-7 text-slate-800">
            {{ question.answer.content }}
          </p>
          <time class="mt-2 block text-xs text-slate-500" :datetime="question.answer.created_at">
            {{ formatDate(question.answer.created_at) }}
          </time>
        </div>
        <p v-else class="mt-4 text-sm font-semibold text-amber-700">Nhà bán chưa trả lời.</p>
      </article>
    </div>

    <div
      v-else-if="!errorMessage"
      class="mt-8 rounded-2xl border border-dashed border-slate-300 px-5 py-12 text-center"
    >
      <ChatBubbleLeftRightIcon class="mx-auto h-10 w-10 text-slate-400" aria-hidden="true" />
      <p class="mt-3 font-bold">Chưa có câu hỏi nào</p>
      <p class="mt-1 text-sm text-slate-500">Hãy là người đầu tiên hỏi về sản phẩm này.</p>
    </div>

    <button
      v-if="errorMessage"
      class="mt-4 text-sm font-bold text-indigo-700"
      type="button"
      @click="loadQuestions(meta.page || 1)"
    >
      Thử tải lại
    </button>

    <nav
      v-if="!loading && meta.total_pages > 1"
      class="mt-7 flex items-center justify-center gap-3"
      aria-label="Phân trang hỏi đáp"
    >
      <button
        class="grid h-10 w-10 place-items-center rounded-xl border border-slate-300 disabled:opacity-40"
        type="button"
        aria-label="Trang hỏi đáp trước"
        :disabled="meta.page <= 1"
        @click="loadQuestions(meta.page - 1)"
      >
        <ChevronLeftIcon class="h-5 w-5" />
      </button>
      <span class="text-sm text-slate-600">
        Trang <strong>{{ meta.page }}</strong> / {{ meta.total_pages }}
      </span>
      <button
        class="grid h-10 w-10 place-items-center rounded-xl border border-slate-300 disabled:opacity-40"
        type="button"
        aria-label="Trang hỏi đáp sau"
        :disabled="meta.page >= meta.total_pages"
        @click="loadQuestions(meta.page + 1)"
      >
        <ChevronRightIcon class="h-5 w-5" />
      </button>
    </nav>
  </section>
</template>
