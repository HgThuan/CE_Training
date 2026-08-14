<script setup lang="ts">
import { ref, watch } from 'vue'
import { ArrowLeftIcon } from '@heroicons/vue/24/outline'

import FormMessage from '@/features/auth/components/FormMessage.vue'
import { getErrorMessage } from '@/features/auth/errors'
import type { SellerApplication, SellerDocument } from '@/features/seller/types'
import { confirmDialog, promptDialog } from '@/shared/composables/useAppDialog'
import type { PaginationMeta } from '@/shared/types/api'

import { adminSellersApi } from '../api'

const props = defineProps<{ status: 'pending' | 'rejected' }>()
const applications = ref<SellerApplication[]>([])
const selected = ref<SellerApplication | null>(null)
const search = ref('')
const meta = ref<PaginationMeta>({ page: 1, page_size: 12, total_items: 0, total_pages: 0 })
const loading = ref(true)
const loadingDetail = ref(false)
const message = ref('')
const errorMessage = ref('')

const verificationLabels = {
  unverified: 'Chưa xác minh',
  pending: 'Đang xác minh',
  verified: 'Đã xác minh',
}
const documentLabels = {
  pending: 'Chờ kiểm tra',
  verified: 'Đã xác minh',
  additional_required: 'Cần bổ sung',
}

function isPreviewable(document: SellerDocument): boolean {
  return /\.(png|jpe?g|webp|gif)(\?.*)?$/i.test(document.file_url)
}

async function loadApplications(page = 1): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await adminSellersApi.listApplications({
      search: search.value || undefined,
      onboarding_status: props.status,
      page,
      page_size: meta.value.page_size,
    })
    applications.value = response.data.data
    selected.value = null
    if (response.data.meta) meta.value = response.data.meta
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
}

async function selectApplication(profileId: number): Promise<void> {
  loadingDetail.value = true
  errorMessage.value = ''
  try {
    selected.value = (await adminSellersApi.getApplication(profileId)).data.data
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loadingDetail.value = false
  }
}

function returnToList(): void {
  selected.value = null
}

async function advanceAfterAction(profileId: number): Promise<void> {
  const currentIndex = applications.value.findIndex((item) => item.id === profileId)
  const currentPage = meta.value.page
  await loadApplications(currentPage)
  if (!applications.value.length && currentPage > 1) {
    await loadApplications(currentPage - 1)
  }
  const next =
    applications.value[Math.min(Math.max(currentIndex, 0), applications.value.length - 1)]
  if (next) await selectApplication(next.id)
}

async function approve(profile: SellerApplication): Promise<void> {
  const confirmed = await confirmDialog({
    title: 'Duyệt hồ sơ seller',
    message: `Xác nhận cho phép “${profile.business_name}” bắt đầu bán hàng?`,
    confirmLabel: 'Duyệt hồ sơ',
  })
  if (!confirmed) return
  try {
    message.value = (await adminSellersApi.approveApplication(profile.id)).data.message
    await advanceAfterAction(profile.id)
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
}

async function reject(profile: SellerApplication): Promise<void> {
  const reason = await promptDialog({
    title: 'Từ chối hồ sơ seller',
    message: profile.business_name,
    inputLabel: 'Lý do để seller biết cần bổ sung hoặc sửa thông tin gì',
    confirmLabel: 'Từ chối hồ sơ',
    destructive: true,
    required: true,
  })
  if (!reason?.trim()) return
  try {
    message.value = (
      await adminSellersApi.rejectApplication(profile.id, reason.trim())
    ).data.message
    await advanceAfterAction(profile.id)
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
}

async function reviewDocument(document: SellerDocument, verified: boolean): Promise<void> {
  const reason = verified
    ? ''
    : await promptDialog({
        title: 'Yêu cầu bổ sung tài liệu',
        inputLabel: 'Nội dung seller cần bổ sung',
        confirmLabel: 'Gửi yêu cầu',
        required: true,
      })
  if (!verified && !reason?.trim()) return
  try {
    await adminSellersApi.reviewDocument(
      document.id,
      verified ? 'verified' : 'additional_required',
      reason?.trim() ?? '',
    )
    if (selected.value) await selectApplication(selected.value.id)
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
}

watch(
  () => props.status,
  () => void loadApplications(1),
  { immediate: true },
)
</script>

<template>
  <FormMessage v-if="message" class="mt-5" :message="message" variant="success" />
  <FormMessage v-if="errorMessage" class="mt-5" :message="errorMessage" />

  <form class="mt-5 flex flex-col gap-3 sm:flex-row" @submit.prevent="loadApplications(1)">
    <label class="min-w-0 flex-1">
      <span class="sr-only">Tìm hồ sơ seller</span>
      <input
        v-model.trim="search"
        class="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
        placeholder="Tìm theo tên doanh nghiệp, email hoặc mã số thuế"
      />
    </label>
    <button class="rounded-xl bg-slate-950 px-6 py-3 font-bold text-white hover:bg-slate-800">
      Tìm hồ sơ
    </button>
  </form>

  <div
    class="mt-5 grid items-start gap-5 xl:h-[calc(100dvh-18rem)] xl:min-h-[28rem] xl:max-h-[46rem] xl:grid-cols-[minmax(320px,0.82fr)_minmax(440px,1.18fr)]"
  >
    <section
      class="h-full min-h-0 flex-col overflow-hidden rounded-2xl bg-white ring-1 ring-slate-200"
      :class="selected ? 'hidden xl:flex' : 'flex'"
      aria-label="Danh sách hồ sơ seller"
    >
      <div class="flex shrink-0 items-center justify-between border-b border-slate-100 px-5 py-4">
        <h2 class="font-black">
          {{ status === 'pending' ? 'Hồ sơ cần xử lý' : 'Hồ sơ đã từ chối' }}
        </h2>
        <span class="text-sm text-slate-500">{{ meta.total_items }} hồ sơ</span>
      </div>
      <p
        v-if="loading"
        class="grid min-h-0 flex-1 place-items-center p-8 text-center text-slate-500"
      >
        Đang tải hồ sơ…
      </p>
      <p
        v-else-if="!applications.length"
        class="grid min-h-0 flex-1 place-items-center p-8 text-center text-slate-500"
      >
        {{
          search
            ? 'Không tìm thấy hồ sơ phù hợp.'
            : status === 'pending'
              ? 'Không có hồ sơ đang chờ duyệt.'
              : 'Chưa có hồ sơ bị từ chối.'
        }}
      </p>
      <div
        v-else
        class="min-h-0 flex-1 divide-y divide-slate-100 overflow-y-auto overscroll-contain"
      >
        <button
          v-for="profile in applications"
          :key="profile.id"
          class="block w-full px-5 py-4 text-left transition-colors hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-indigo-600"
          :class="selected?.id === profile.id ? 'bg-indigo-50' : ''"
          type="button"
          @click="selectApplication(profile.id)"
        >
          <span class="block font-bold text-slate-950">{{ profile.business_name }}</span>
          <span class="mt-2 flex flex-wrap items-center gap-2 text-xs">
            <span class="rounded-full bg-indigo-50 px-2.5 py-1 font-bold text-indigo-700">{{
              verificationLabels[profile.verification_status]
            }}</span>
            <span class="text-slate-500">MST: {{ profile.tax_code || 'Chưa có' }}</span>
          </span>
          <span class="mt-2 block text-xs text-slate-500"
            >Nộp
            {{
              profile.submitted_at
                ? new Date(profile.submitted_at).toLocaleString('vi-VN')
                : 'chưa xác định'
            }}</span
          >
        </button>
      </div>
      <nav
        v-if="meta.total_pages > 1"
        class="flex shrink-0 items-center justify-between border-t border-slate-100 bg-white px-5 py-4 text-sm"
      >
        <span>Trang {{ meta.page }}/{{ meta.total_pages }}</span>
        <div class="flex gap-2">
          <button
            class="rounded-lg border border-slate-300 px-3 py-2 disabled:opacity-40"
            type="button"
            :disabled="meta.page <= 1"
            @click="loadApplications(meta.page - 1)"
          >
            Trước</button
          ><button
            class="rounded-lg border border-slate-300 px-3 py-2 disabled:opacity-40"
            type="button"
            :disabled="meta.page >= meta.total_pages"
            @click="loadApplications(meta.page + 1)"
          >
            Sau
          </button>
        </div>
      </nav>
    </section>

    <section
      class="h-full min-h-0 overflow-hidden rounded-2xl bg-white ring-1 ring-slate-200 xl:sticky xl:top-6"
      :class="selected ? 'block' : 'hidden xl:block'"
      aria-label="Chi tiết hồ sơ seller"
    >
      <p v-if="loadingDetail" class="grid min-h-64 place-items-center text-slate-500">
        Đang tải chi tiết…
      </p>
      <div v-else-if="selected" class="flex h-full min-h-0 flex-col">
        <div class="min-h-0 flex-1 overflow-y-auto overscroll-contain p-5 sm:p-6">
          <button
            class="mb-5 inline-flex items-center gap-2 font-bold text-indigo-700 xl:hidden"
            type="button"
            @click="returnToList"
          >
            <ArrowLeftIcon class="h-4 w-4" />Quay lại danh sách
          </button>
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 class="text-2xl font-black text-slate-950">{{ selected.business_name }}</h2>
              <p class="mt-1 text-sm text-slate-500">Hồ sơ #{{ selected.id }}</p>
            </div>
            <span
              class="rounded-full px-3 py-1 text-xs font-bold"
              :class="
                selected.onboarding_status === 'rejected'
                  ? 'bg-rose-50 text-rose-700'
                  : 'bg-amber-50 text-amber-700'
              "
              >{{ selected.onboarding_status === 'rejected' ? 'Đã từ chối' : 'Chờ duyệt' }}</span
            >
          </div>
          <dl class="mt-6 grid gap-x-6 gap-y-4 text-sm sm:grid-cols-2">
            <div>
              <dt class="text-slate-500">Địa chỉ</dt>
              <dd class="mt-1 font-semibold text-slate-900">
                {{ selected.business_address || 'Chưa cung cấp' }}
              </dd>
            </div>
            <div>
              <dt class="text-slate-500">Mã số thuế</dt>
              <dd class="mt-1 font-semibold text-slate-900">
                {{ selected.tax_code || 'Chưa cung cấp' }}
              </dd>
            </div>
            <div>
              <dt class="text-slate-500">Điện thoại</dt>
              <dd class="mt-1 font-semibold text-slate-900">
                {{ selected.contact_phone || 'Chưa cung cấp' }}
              </dd>
            </div>
            <div v-if="selected.rejection_reason">
              <dt class="text-slate-500">Lý do từ chối</dt>
              <dd class="mt-1 font-semibold text-rose-700">{{ selected.rejection_reason }}</dd>
            </div>
          </dl>
          <div class="mt-7 border-t border-slate-100 pt-6">
            <h3 class="font-black">Giấy tờ xác minh</h3>
            <p
              v-if="!selected.documents.length"
              class="mt-3 rounded-xl bg-amber-50 p-4 text-sm text-amber-800"
            >
              Hồ sơ chưa có giấy tờ. Không nên duyệt trước khi seller bổ sung tài liệu.
            </p>
            <div v-else class="mt-3 grid gap-3 sm:grid-cols-2">
              <article
                v-for="document in selected.documents"
                :key="document.id"
                class="rounded-xl bg-slate-50 p-4"
              >
                <a v-if="isPreviewable(document)" :href="document.file_url" target="_blank"
                  ><img
                    :src="document.file_url"
                    :alt="document.original_name"
                    class="mb-3 h-36 w-full rounded-lg bg-white object-contain" /></a
                ><a
                  class="line-clamp-2 font-bold text-indigo-700"
                  :href="document.file_url"
                  target="_blank"
                  >{{ document.original_name }}</a
                >
                <p class="mt-1 text-xs text-slate-500">
                  {{ documentLabels[document.review_status] }}
                </p>
                <div v-if="status === 'pending'" class="mt-3 flex flex-wrap gap-2">
                  <button
                    class="rounded-lg bg-emerald-600 px-3 py-2 text-xs font-bold text-white"
                    type="button"
                    @click="reviewDocument(document, true)"
                  >
                    Xác minh</button
                  ><button
                    class="rounded-lg border border-slate-300 px-3 py-2 text-xs font-bold"
                    type="button"
                    @click="reviewDocument(document, false)"
                  >
                    Yêu cầu bổ sung
                  </button>
                </div>
              </article>
            </div>
          </div>
        </div>
        <div
          v-if="status === 'pending'"
          class="flex shrink-0 flex-wrap gap-3 border-t border-slate-100 bg-white p-5 sm:px-6"
        >
          <button
            class="rounded-xl bg-indigo-600 px-5 py-3 font-bold text-white hover:bg-indigo-700"
            type="button"
            @click="approve(selected)"
          >
            Duyệt hồ sơ</button
          ><button
            class="rounded-xl border border-rose-300 px-5 py-3 font-bold text-rose-700 hover:bg-rose-50"
            type="button"
            @click="reject(selected)"
          >
            Từ chối
          </button>
        </div>
      </div>
      <p v-else class="grid min-h-64 place-items-center text-center text-slate-500">
        Chọn một hồ sơ trong danh sách để xem thông tin và giấy tờ.
      </p>
    </section>
  </div>
</template>
