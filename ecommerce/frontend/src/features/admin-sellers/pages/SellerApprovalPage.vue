<script setup lang="ts">
import { onMounted, ref } from 'vue'

import FormMessage from '@/features/auth/components/FormMessage.vue'
import { getErrorMessage } from '@/features/auth/errors'
import type { SellerApplication, SellerDocument } from '@/features/seller/types'
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

const dialogConfig = ref({
  isOpen: false,
  title: '',
  message: '',
  isPrompt: false,
  inputValue: '',
  resolve: null as ((value: string | boolean | null) => void) | null,
})

function openConfirm(title: string, message: string): Promise<boolean> {
  return new Promise((resolve) => {
    dialogConfig.value = {
      isOpen: true,
      title,
      message,
      isPrompt: false,
      inputValue: '',
      resolve: (value) => resolve(Boolean(value)),
    }
  })
}

function openPrompt(title: string, message: string): Promise<string | null> {
  return new Promise((resolve) => {
    dialogConfig.value = {
      isOpen: true,
      title,
      message,
      isPrompt: true,
      inputValue: '',
      resolve: (value) => resolve(typeof value === 'string' ? value : null),
    }
  })
}

function closeDialog(result: string | boolean | null): void {
  dialogConfig.value.resolve?.(result)
  dialogConfig.value.isOpen = false
  dialogConfig.value.resolve = null
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
  const confirmed = await openConfirm('Xác nhận duyệt', `Duyệt gian hàng ${profile.business_name}?`)
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
  const reason = await openPrompt('Từ chối hồ sơ', 'Nhập lý do từ chối:')
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
  const reason = verified ? '' : await openPrompt('Yêu cầu bổ sung', 'Mô tả nội dung cần bổ sung:')
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
    <p class="mt-5 text-sm font-bold uppercase tracking-[0.2em] text-indigo-600">ADM-09 · ADM-10</p>
    <h1 class="mt-2 text-3xl font-bold">Duyệt hồ sơ seller</h1>
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
          <span class="mt-1 block text-sm text-gray-600">
            {{ profile.tax_code }} · {{ profile.verification_status }}
          </span>
        </button>
      </section>

      <section v-if="selected" class="rounded-2xl bg-white p-6 ring-1 ring-gray-200">
        <h2 class="text-2xl font-bold">{{ selected.business_name }}</h2>
        <dl class="mt-4 grid gap-2 text-sm">
          <div>
            <dt class="font-bold">Địa chỉ</dt>
            <dd>{{ selected.business_address }}</dd>
          </div>
          <div>
            <dt class="font-bold">Mã số thuế</dt>
            <dd>{{ selected.tax_code }}</dd>
          </div>
          <div>
            <dt class="font-bold">Điện thoại</dt>
            <dd>{{ selected.contact_phone }}</dd>
          </div>
        </dl>
        <h3 class="mt-6 font-bold">Giấy tờ</h3>
        <article
          v-for="document in selected.documents"
          :key="document.id"
          class="mt-3 rounded-xl bg-gray-50 p-4"
        >
          <a class="font-semibold text-indigo-600" :href="document.file_url" target="_blank">
            {{ document.original_name }}
          </a>
          <p class="mt-1 text-sm">{{ document.review_status }}</p>
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
    </div>

    <div
      v-if="dialogConfig.isOpen"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="presentation"
      @click.self="closeDialog(null)"
    >
      <section
        aria-labelledby="seller-dialog-title"
        aria-modal="true"
        class="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl"
        role="dialog"
        @keyup.esc="closeDialog(null)"
      >
        <h2 id="seller-dialog-title" class="text-xl font-bold">{{ dialogConfig.title }}</h2>
        <p class="mt-2 text-gray-600">{{ dialogConfig.message }}</p>

        <input
          v-if="dialogConfig.isPrompt"
          v-model="dialogConfig.inputValue"
          autofocus
          class="mt-4 w-full rounded-xl border px-3 py-2.5 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          placeholder="Nhập nội dung..."
          type="text"
          @keyup.enter="closeDialog(dialogConfig.inputValue)"
        />

        <div class="mt-6 flex justify-end gap-3">
          <button
            class="rounded-xl border px-5 py-2.5 font-bold hover:bg-gray-50"
            type="button"
            @click="closeDialog(null)"
          >
            Hủy
          </button>
          <button
            class="rounded-xl bg-indigo-600 px-5 py-2.5 font-bold text-white hover:bg-indigo-700"
            type="button"
            @click="closeDialog(dialogConfig.isPrompt ? dialogConfig.inputValue : true)"
          >
            Xác nhận
          </button>
        </div>
      </section>
    </div>
  </main>
</template>
