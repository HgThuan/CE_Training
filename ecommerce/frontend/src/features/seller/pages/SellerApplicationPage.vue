<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import FormMessage from '@/features/auth/components/FormMessage.vue'
import { getErrorMessage } from '@/features/auth/errors'

import { sellerApi } from '../api'
import type { SellerApplication, SellerApplicationPayload, SellerDocument } from '../types'

const application = ref<SellerApplication | null>(null)
const loading = ref(true)
const saving = ref(false)
const message = ref('')
const errorMessage = ref('')
const documentType = ref<SellerDocument['document_type']>('id_card')
const documentFile = ref<File | null>(null)
const form = reactive<SellerApplicationPayload>({
  business_name: '',
  business_address: '',
  tax_code: '',
  contact_phone: '',
})

async function loadApplication(): Promise<void> {
  loading.value = true
  try {
    application.value = (await sellerApi.getApplication()).data.data
    if (application.value?.onboarding_status === 'rejected') {
      Object.assign(form, {
        business_name: application.value.business_name,
        business_address: application.value.business_address,
        tax_code: application.value.tax_code,
        contact_phone: application.value.contact_phone,
      })
    }
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
}

async function submitApplication(): Promise<void> {
  saving.value = true
  errorMessage.value = ''
  try {
    const response = await sellerApi.submitApplication({ ...form })
    application.value = response.data.data
    message.value = 'Bước 1 hoàn tất. Hãy tải giấy tờ xác minh ở bước 2.'
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    saving.value = false
  }
}

function selectFile(event: Event): void {
  const input = event.target as HTMLInputElement
  documentFile.value = input.files?.[0] ?? null
}

async function uploadDocument(): Promise<void> {
  if (!documentFile.value) return
  saving.value = true
  errorMessage.value = ''
  try {
    const response = await sellerApi.uploadDocument(documentType.value, documentFile.value)
    if (application.value) application.value.documents.push(response.data.data)
    documentFile.value = null
    message.value = response.data.message
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    saving.value = false
  }
}

onMounted(loadApplication)
</script>

<template>
  <main class="mx-auto max-w-4xl px-4 py-10">
    <p class="text-sm font-bold uppercase tracking-[0.2em] text-indigo-600">SEL-18</p>
    <h1 class="mt-2 text-3xl font-bold">Đăng ký trở thành nhà bán hàng</h1>
    <p class="mt-2 text-gray-600">Hoàn thành thông tin doanh nghiệp và tải giấy tờ xác minh.</p>

    <FormMessage v-if="message" class="mt-6" :message="message" variant="success" />
    <FormMessage v-if="errorMessage" class="mt-6" :message="errorMessage" />
    <p v-if="loading" class="mt-8">Đang tải hồ sơ…</p>

    <section
      v-else-if="application?.onboarding_status === 'approved'"
      class="mt-8 rounded-2xl bg-emerald-50 p-6 ring-1 ring-emerald-200"
    >
      <h2 class="text-xl font-bold text-emerald-900">Hồ sơ đã được duyệt</h2>
      <p class="mt-2 text-emerald-800">Đăng nhập lại để nhận role Seller và quản lý gian hàng.</p>
    </section>

    <template v-else>
      <section
        v-if="application?.onboarding_status === 'pending'"
        class="mt-8 rounded-2xl bg-amber-50 p-6 ring-1 ring-amber-200"
      >
        <h2 class="text-xl font-bold text-amber-950">Hồ sơ đang chờ duyệt</h2>
        <p class="mt-2 text-amber-900">Bạn vẫn có thể thay thế giấy tờ trước khi Admin xử lý.</p>
      </section>

      <section
        v-if="application?.onboarding_status === 'rejected'"
        class="mt-8 rounded-2xl bg-red-50 p-6 ring-1 ring-red-200"
      >
        <h2 class="text-xl font-bold text-red-950">Hồ sơ cần chỉnh sửa</h2>
        <p class="mt-2 text-red-900">{{ application.rejection_reason }}</p>
      </section>

      <form
        v-if="!application || application.onboarding_status === 'rejected'"
        class="mt-8 grid gap-5 rounded-2xl bg-white p-6 ring-1 ring-gray-200 sm:grid-cols-2"
        data-testid="application-form"
        @submit.prevent="submitApplication"
      >
        <h2 class="text-xl font-bold sm:col-span-2">Bước 1 · Thông tin kinh doanh</h2>
        <label class="text-sm font-semibold"
          >Tên gian hàng
          <input
            v-model.trim="form.business_name"
            class="mt-2 w-full rounded-xl border px-3 py-2.5"
            required
        /></label>
        <label class="text-sm font-semibold"
          >Mã số thuế
          <input
            v-model.trim="form.tax_code"
            class="mt-2 w-full rounded-xl border px-3 py-2.5"
            required
        /></label>
        <label class="text-sm font-semibold"
          >Số điện thoại
          <input
            v-model.trim="form.contact_phone"
            class="mt-2 w-full rounded-xl border px-3 py-2.5"
            required
        /></label>
        <label class="text-sm font-semibold sm:col-span-2"
          >Địa chỉ kinh doanh
          <textarea
            v-model.trim="form.business_address"
            class="mt-2 w-full rounded-xl border px-3 py-2.5"
            required
          />
        </label>
        <button
          class="rounded-xl bg-indigo-600 px-4 py-3 font-bold text-white disabled:opacity-60 sm:col-span-2"
          :disabled="saving"
        >
          Gửi thông tin
        </button>
      </form>

      <form
        v-if="application"
        class="mt-8 grid gap-5 rounded-2xl bg-white p-6 ring-1 ring-gray-200 sm:grid-cols-2"
        data-testid="document-form"
        @submit.prevent="uploadDocument"
      >
        <h2 class="text-xl font-bold sm:col-span-2">Bước 2 · Giấy tờ xác minh</h2>
        <select v-model="documentType" class="rounded-xl border px-3 py-2.5">
          <option value="id_card">CCCD/CMND</option>
          <option value="business_license">Giấy phép kinh doanh</option>
          <option value="tax_registration">Đăng ký thuế</option>
          <option value="other">Khác</option>
        </select>
        <input accept=".jpg,.jpeg,.png,.pdf" required type="file" @change="selectFile" />
        <button
          class="rounded-xl bg-gray-950 px-4 py-3 font-bold text-white disabled:opacity-60 sm:col-span-2"
          :disabled="saving || !documentFile"
        >
          Tải giấy tờ
        </button>
        <ul v-if="application.documents.length" class="space-y-2 sm:col-span-2">
          <li
            v-for="document in application.documents"
            :key="document.id"
            class="rounded-xl bg-gray-50 p-3 text-sm"
          >
            {{ document.original_name }} · {{ document.review_status }}
            <span v-if="document.review_reason"> — {{ document.review_reason }}</span>
          </li>
        </ul>
      </form>
    </template>
  </main>
</template>
