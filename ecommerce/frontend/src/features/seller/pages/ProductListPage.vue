<script setup lang="ts">
import {
  MagnifyingGlassIcon,
  PencilSquareIcon,
  PlusIcon,
  TrashIcon,
} from '@heroicons/vue/24/outline'
import { onMounted, ref } from 'vue'

import FormMessage from '@/features/auth/components/FormMessage.vue'
import { getErrorMessage } from '@/features/auth/errors'
import type {
  ProductStatus,
  SellerProductListItem,
  SellerProductFilters,
} from '@/features/product/types'
import { showConfirm } from '@/shared/lib/dialog'
import { formatDateTime, formatVnd } from '@/shared/lib/formatters'
import type { PaginationMeta } from '@/shared/types/api'

import { sellerProductApi } from '../product-api'

const products = ref<SellerProductListItem[]>([])
const search = ref('')
const status = ref<ProductStatus | ''>('')
const meta = ref<PaginationMeta>({
  page: 1,
  page_size: 20,
  total_items: 0,
  total_pages: 0,
})
const loading = ref(true)
const actionId = ref('')
const message = ref('')
const errorMessage = ref('')

const statusLabels: Record<ProductStatus, string> = {
  draft: 'Bản nháp',
  pending_review: 'Chờ duyệt',
  approved: 'Đã duyệt',
  rejected: 'Bị từ chối',
  hidden: 'Đã ẩn',
  suspended: 'Tạm ngưng',
}
const statusClasses: Record<ProductStatus, string> = {
  draft: 'bg-slate-100 text-slate-700',
  pending_review: 'bg-amber-100 text-amber-800',
  approved: 'bg-emerald-100 text-emerald-800',
  rejected: 'bg-rose-100 text-rose-800',
  hidden: 'bg-violet-100 text-violet-800',
  suspended: 'bg-orange-100 text-orange-800',
}

async function loadProducts(page = 1): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  const filters: SellerProductFilters = {
    search: search.value || undefined,
    status: status.value || undefined,
    sort: '-created_at',
    page,
    page_size: meta.value.page_size,
  }
  try {
    const response = await sellerProductApi.list(filters)
    products.value = response.data.data
    if (response.data.meta) meta.value = response.data.meta
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
}

async function submitForReview(product: SellerProductListItem): Promise<void> {
  actionId.value = product.id
  message.value = ''
  errorMessage.value = ''
  try {
    const response = await sellerProductApi.submit(product.id)
    message.value = response.data.message
    await loadProducts(meta.value.page)
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    actionId.value = ''
  }
}

async function deleteProduct(product: SellerProductListItem): Promise<void> {
  if (!(await showConfirm(`Xóa mềm sản phẩm “${product.name}”?`, { tone: 'danger' }))) return
  actionId.value = product.id
  message.value = ''
  errorMessage.value = ''
  try {
    const response = await sellerProductApi.delete(product.id)
    message.value = response.data.message
    await loadProducts(meta.value.page)
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    actionId.value = ''
  }
}

onMounted(loadProducts)
</script>

<template>
  <main class="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:py-10">
    <div class="flex flex-wrap items-end justify-between gap-5">
      <div>
        <p class="text-sm font-bold uppercase tracking-[0.2em] text-indigo-600">SEL-02 · SEL-05</p>
        <h1 class="mt-2 text-3xl font-black tracking-tight text-slate-950 sm:text-4xl">
          Sản phẩm của tôi
        </h1>
        <p class="mt-3 text-slate-600">
          Tạo nội dung, quản lý media, biến thể và trạng thái duyệt.
        </p>
      </div>
      <RouterLink
        class="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 font-bold text-white shadow-sm hover:bg-indigo-700"
        to="/seller/products/new"
      >
        <PlusIcon class="h-5 w-5" />
        Thêm sản phẩm
      </RouterLink>
    </div>

    <FormMessage v-if="message" class="mt-6" :message="message" variant="success" />
    <FormMessage v-if="errorMessage" class="mt-6" :message="errorMessage" />

    <form
      class="mt-8 flex flex-wrap gap-3 rounded-2xl bg-white p-4 ring-1 ring-slate-200"
      @submit.prevent="loadProducts(1)"
    >
      <label class="relative min-w-64 flex-1">
        <span class="sr-only">Tìm sản phẩm</span>
        <MagnifyingGlassIcon
          class="pointer-events-none absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400"
        />
        <input
          v-model.trim="search"
          class="w-full rounded-xl border border-slate-300 py-2.5 pl-10 pr-3"
          placeholder="Tìm theo tên sản phẩm"
        />
      </label>
      <select v-model="status" class="rounded-xl border border-slate-300 bg-white px-3 py-2.5">
        <option value="">Mọi trạng thái</option>
        <option v-for="(label, key) in statusLabels" :key="key" :value="key">{{ label }}</option>
      </select>
      <button class="rounded-xl bg-slate-950 px-5 py-2.5 font-bold text-white">Lọc</button>
    </form>

    <div class="mt-6 overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-slate-200">
      <div class="overflow-x-auto">
        <table class="w-full min-w-[900px] text-left text-sm">
          <thead class="bg-slate-50 text-xs uppercase tracking-wider text-slate-500">
            <tr>
              <th class="px-5 py-4">Sản phẩm</th>
              <th class="px-4 py-4">Giá</th>
              <th class="px-4 py-4">Trạng thái</th>
              <th class="px-4 py-4">Ngày tạo</th>
              <th class="px-5 py-4 text-right">Thao tác</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-if="loading">
              <td class="px-5 py-10 text-center text-slate-500" colspan="5">Đang tải sản phẩm…</td>
            </tr>
            <tr v-else-if="!products.length">
              <td class="px-5 py-14 text-center" colspan="5">
                <p class="font-bold text-slate-900">Chưa có sản phẩm phù hợp</p>
                <p class="mt-1 text-slate-500">Tạo sản phẩm đầu tiên hoặc thử bộ lọc khác.</p>
              </td>
            </tr>
            <tr v-for="product in products" :key="product.id" class="hover:bg-slate-50/70">
              <td class="px-5 py-4">
                <div class="flex items-center gap-3">
                  <img
                    v-if="product.thumbnail"
                    :src="product.thumbnail"
                    :alt="product.name"
                    class="h-14 w-14 rounded-xl bg-slate-100 object-cover ring-1 ring-slate-200"
                  />
                  <div v-else class="h-14 w-14 rounded-xl bg-slate-100" />
                  <div>
                    <strong class="line-clamp-1 text-slate-950">{{ product.name }}</strong>
                    <span class="mt-1 block text-xs text-slate-500">{{ product.slug }}</span>
                  </div>
                </div>
              </td>
              <td class="px-4 py-4 font-semibold">
                {{ formatVnd(product.min_price) }}
                <span
                  v-if="product.max_price && product.max_price !== product.min_price"
                  class="block text-xs font-normal text-slate-500"
                >
                  – {{ formatVnd(product.max_price) }}
                </span>
              </td>
              <td class="px-4 py-4">
                <span
                  class="inline-flex rounded-full px-2.5 py-1 text-xs font-bold"
                  :class="statusClasses[product.status]"
                >
                  {{ statusLabels[product.status] }}
                </span>
              </td>
              <td class="px-4 py-4 text-slate-600">{{ formatDateTime(product.created_at) }}</td>
              <td class="px-5 py-4">
                <div class="flex justify-end gap-2">
                  <RouterLink
                    v-if="['draft', 'rejected'].includes(product.status)"
                    class="grid h-9 w-9 place-items-center rounded-lg border border-slate-300 text-slate-700 hover:border-indigo-600 hover:text-indigo-700"
                    :to="`/seller/products/${product.id}/edit`"
                    aria-label="Sửa sản phẩm"
                  >
                    <PencilSquareIcon class="h-4 w-4" />
                  </RouterLink>
                  <button
                    v-if="product.status === 'draft'"
                    class="rounded-lg bg-indigo-50 px-3 py-2 text-xs font-bold text-indigo-700 hover:bg-indigo-100 disabled:opacity-50"
                    type="button"
                    :disabled="actionId === product.id"
                    @click="submitForReview(product)"
                  >
                    Gửi duyệt
                  </button>
                  <button
                    v-if="['draft', 'hidden'].includes(product.status)"
                    class="grid h-9 w-9 place-items-center rounded-lg border border-rose-200 text-rose-700 hover:bg-rose-50 disabled:opacity-50"
                    type="button"
                    :disabled="actionId === product.id"
                    aria-label="Xóa sản phẩm"
                    @click="deleteProduct(product)"
                  >
                    <TrashIcon class="h-4 w-4" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <nav
      v-if="meta.total_pages > 1"
      class="mt-6 flex items-center justify-end gap-3 text-sm"
      aria-label="Phân trang sản phẩm seller"
    >
      <button
        class="rounded-xl border bg-white px-4 py-2 font-bold disabled:opacity-40"
        :disabled="meta.page <= 1"
        @click="loadProducts(meta.page - 1)"
      >
        Trước
      </button>
      <span>Trang {{ meta.page }} / {{ meta.total_pages }}</span>
      <button
        class="rounded-xl border bg-white px-4 py-2 font-bold disabled:opacity-40"
        :disabled="meta.page >= meta.total_pages"
        @click="loadProducts(meta.page + 1)"
      >
        Sau
      </button>
    </nav>
  </main>
</template>
