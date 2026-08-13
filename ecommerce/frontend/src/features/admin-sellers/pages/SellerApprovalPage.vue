<script setup lang="ts">
import { onMounted, ref } from 'vue'

import FormMessage from '@/features/auth/components/FormMessage.vue'
import { getErrorMessage } from '@/features/auth/errors'
import type { SellerApplication, SellerDocument } from '@/features/seller/types'
import { confirmDialog, promptDialog } from '@/shared/composables/useAppDialog'
import type { PaginationMeta } from '@/shared/types/api'

import { adminSellersApi } from '../api'

const applications = ref<SellerApplication[]>([])
const selected = ref<SellerApplication | null>(null)
const status = ref<'pending' | 'approved' | 'rejected'>('pending')
const search = ref('')
const meta = ref<PaginationMeta>({ page: 1, page_size: 20, total_items: 0, total_pages: 0 })
const loading = ref(true)
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
  try {
    const response = await adminSellersApi.listApplications({
      search: search.value || undefined,
      onboarding_status: status.value,
      page,
      page_size: meta.value.page_size,
    })
    applications.value = response.data.data
    if (response.data.meta) meta.value = response.data.meta
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
}

async function selectApplication(profileId: number): Promise<void> {
  try {
    selected.value = (await adminSellersApi.getApplication(profileId)).data.data
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
}

async function approve(profile: SellerApplication): Promise<void> {
  const confirmed = await confirmDialog({
    title: 'Duyệt gian hàng',
    message: `Xác nhận duyệt gian hàng ${profile.business_name}?`,
    confirmLabel: 'Duyệt gian hàng',
  })
  if (!confirmed) return
  try {
    message.value = (await adminSellersApi.approveApplication(profile.id)).data.message
    selected.value = null
    await loadApplications(meta.value.page)
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
}

async function reject(profile: SellerApplication): Promise<void> {
  const reason = await promptDialog({
    title: 'Từ chối hồ sơ seller',
    inputLabel: 'Lý do từ chối',
    confirmLabel: 'Từ chối hồ sơ',
    destructive: true,
    required: true,
  })
  if (!reason?.trim()) return
  try {
    message.value = (
      await adminSellersApi.rejectApplication(profile.id, reason.trim())
    ).data.message
    selected.value = null
    await loadApplications(meta.value.page)
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
}

async function reviewDocument(document: SellerDocument, verified: boolean): Promise<void> {
  const reason = verified
    ? ''
    : await promptDialog({
        title: 'Yêu cầu bổ sung tài liệu',
        inputLabel: 'Nội dung cần bổ sung',
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

onMounted(loadApplications)
</script>

<template>
  <main class="mx-auto max-w-7xl px-4 py-10">
    <RouterLink class="font-semibold text-indigo-600" to="/admin">← Admin workspace</RouterLink>
    <h1 class="mt-6 text-3xl font-bold">Duyệt hồ sơ seller</h1>
    <FormMessage v-if="message" class="mt-6" :message="message" variant="success" />
    <FormMessage v-if="errorMessage" class="mt-6" :message="errorMessage" />

    <form class="mt-8 flex flex-wrap gap-3" @submit.prevent="loadApplications(1)">
      <input
        v-model.trim="search"
        aria-label="Tìm hồ sơ seller"
        class="min-w-64 flex-1 rounded-xl border px-3 py-2.5"
        placeholder="Tên shop, email, mã số thuế"
      />
      <select v-model="status" class="rounded-xl border px-3 py-2.5">
        <option value="pending">Chờ duyệt</option>
        <option value="approved">Đã duyệt</option>
        <option value="rejected">Từ chối</option>
      </select>
      <button class="rounded-xl bg-gray-950 px-5 py-2.5 font-bold text-white">Lọc</button>
    </form>

    <div class="mt-6 grid gap-6 lg:grid-cols-[1fr_1.1fr]">
      <section class="rounded-2xl bg-white p-5 ring-1 ring-gray-200">
        <p v-if="loading">Đang tải…</p>
        <p v-else-if="!applications.length" class="text-gray-500">Không có hồ sơ phù hợp.</p>
        <button
          v-for="profile in applications"
          :key="profile.id"
          class="mb-3 block w-full rounded-xl border p-4 text-left hover:border-indigo-500"
          type="button"
          @click="selectApplication(profile.id)"
        >
          <strong>{{ profile.business_name }}</strong>
          <span class="mt-2 flex flex-wrap gap-2 text-xs"
            ><span class="rounded-full bg-indigo-50 px-2 py-1 font-bold text-indigo-700">{{
              verificationLabels[profile.verification_status]
            }}</span
            ><span class="rounded-full bg-slate-100 px-2 py-1 text-slate-600">{{
              profile.tax_code
            }}</span></span
          >
          <span class="mt-2 block text-xs text-slate-500"
            >Nộp
            {{
              profile.submitted_at
                ? new Date(profile.submitted_at).toLocaleString('vi-VN')
                : 'chưa xác định'
            }}</span
          >
        </button>
        <nav v-if="meta.total_pages > 1" class="mt-4 flex items-center justify-between text-sm">
          <span>{{ meta.total_items }} hồ sơ</span>
          <div class="flex gap-2">
            <button
              class="rounded-lg border px-3 py-2 disabled:opacity-40"
              :disabled="meta.page <= 1"
              @click="loadApplications(meta.page - 1)"
            >
              Trước</button
            ><button
              class="rounded-lg border px-3 py-2 disabled:opacity-40"
              :disabled="meta.page >= meta.total_pages"
              @click="loadApplications(meta.page + 1)"
            >
              Sau
            </button>
          </div>
        </nav>
      </section>

      <section v-if="selected" class="rounded-2xl bg-white p-6 ring-1 ring-gray-200">
        <h2 class="text-2xl font-bold">{{ selected.business_name }}</h2>
        <dl class="mt-4 grid gap-2 text-sm">
          <div>
            <dt class="font-bold">Địa chỉ</dt>
            <dd class="mt-1 text-slate-700">{{ selected.business_address || 'Chưa cung cấp' }}</dd>
          </div>
          <div>
            <dt class="font-bold">Mã số thuế</dt>
            <dd class="mt-1 text-slate-700">{{ selected.tax_code || 'Chưa cung cấp' }}</dd>
          </div>
          <div>
            <dt class="font-bold">Điện thoại</dt>
            <dd class="mt-1 text-slate-700">{{ selected.contact_phone || 'Chưa cung cấp' }}</dd>
          </div>
        </dl>
        <h3 class="mt-6 font-bold">Giấy tờ</h3>
        <p
          v-if="!selected.documents.length"
          class="mt-3 rounded-xl bg-amber-50 p-4 text-sm text-amber-800"
        >
          Hồ sơ chưa có giấy tờ đính kèm. Không nên duyệt trước khi seller bổ sung tài liệu xác
          minh.
        </p>
        <article
          v-for="document in selected.documents"
          :key="document.id"
          class="mt-3 rounded-xl bg-gray-50 p-4"
        >
          <a v-if="isPreviewable(document)" :href="document.file_url" target="_blank"
            ><img
              :src="document.file_url"
              :alt="document.original_name"
              class="mb-3 max-h-64 w-full rounded-lg object-contain bg-white"
          /></a>
          <a class="font-semibold text-indigo-600" :href="document.file_url" target="_blank">
            {{ document.original_name }} · Xem toàn màn hình
          </a>
          <p class="mt-1 text-sm">{{ documentLabels[document.review_status] }}</p>
          <div class="mt-3 flex gap-2">
            <button
              class="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-bold text-white"
              type="button"
              @click="reviewDocument(document, true)"
            >
              Xác minh
            </button>
            <button
              class="rounded-lg border px-3 py-2 text-sm font-bold"
              type="button"
              @click="reviewDocument(document, false)"
            >
              Yêu cầu bổ sung
            </button>
          </div>
        </article>
        <div v-if="selected.onboarding_status === 'pending'" class="mt-6 flex gap-3">
          <button
            class="rounded-xl bg-indigo-600 px-5 py-3 font-bold text-white"
            type="button"
            @click="approve(selected)"
          >
            Duyệt hồ sơ
          </button>
          <button
            class="rounded-xl border px-5 py-3 font-bold"
            type="button"
            @click="reject(selected)"
          >
            Từ chối
          </button>
        </div>
      </section>
      <section
        v-else
        class="grid min-h-72 place-items-center rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center text-slate-500"
      >
        Chọn một hồ sơ để xem thông tin và giấy tờ xác minh.
      </section>
    </div>
  </main>
</template>
