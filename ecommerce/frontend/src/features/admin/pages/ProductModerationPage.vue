<script setup lang="ts">
import {
  CheckIcon,
  ClockIcon,
  EyeSlashIcon,
  MagnifyingGlassIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'
import { computed, onMounted, ref } from 'vue'

import FormMessage from '@/features/auth/components/FormMessage.vue'
import { getErrorMessage } from '@/features/auth/errors'
import type { AdminProductListItem } from '@/features/product/types'
import { formatDateTime, formatVnd } from '@/shared/lib/formatters'
import type { PaginationMeta } from '@/shared/types/api'

import { adminCatalogApi } from '../api'

const products = ref<AdminProductListItem[]>([])
const selected = ref<AdminProductListItem | null>(null)
const rejectionTarget = ref<AdminProductListItem | null>(null)
const rejectionReason = ref('')
const search = ref('')
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

const filteredProducts = computed(() => {
  const query = search.value.trim().toLocaleLowerCase('vi')
  if (!query) return products.value
  return products.value.filter((product) =>
    [product.name, product.shop_name, product.seller_name, product.seller_email]
      .join(' ')
      .toLocaleLowerCase('vi')
      .includes(query),
  )
})

async function loadProducts(page = 1): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await adminCatalogApi.pendingProducts(page)
    products.value = response.data.data
    if (response.data.meta) meta.value = response.data.meta
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
}

async function approve(product: AdminProductListItem): Promise<void> {
  actionId.value = product.id
  message.value = ''
  errorMessage.value = ''
  try {
    message.value = (await adminCatalogApi.approveProduct(product.id)).data.message
    selected.value = null
    await loadProducts(meta.value.page)
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    actionId.value = ''
  }
}

function openReject(product: AdminProductListItem): void {
  rejectionTarget.value = product
  rejectionReason.value = ''
}

async function reject(): Promise<void> {
  if (!rejectionTarget.value || !rejectionReason.value.trim()) return
  actionId.value = rejectionTarget.value.id
  message.value = ''
  errorMessage.value = ''
  try {
    message.value = (
      await adminCatalogApi.rejectProduct(rejectionTarget.value.id, rejectionReason.value.trim())
    ).data.message
    rejectionTarget.value = null
    selected.value = null
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
        <p class="text-sm font-bold uppercase tracking-[0.2em] text-indigo-600">ADM-13 · ADM-14</p>
        <h1 class="mt-2 text-3xl font-black tracking-tight sm:text-4xl">Kiểm duyệt sản phẩm</h1>
        <p class="mt-3 text-slate-600">
          Rà soát sản phẩm seller gửi và đưa ra quyết định minh bạch.
        </p>
      </div>
      <div class="rounded-2xl bg-amber-50 px-5 py-3 ring-1 ring-amber-200">
        <p class="text-xs font-bold uppercase tracking-wider text-amber-700">Đang chờ</p>
        <p class="mt-1 text-2xl font-black text-amber-950">{{ meta.total_items }}</p>
      </div>
    </div>

    <FormMessage v-if="message" class="mt-6" :message="message" variant="success" />
    <FormMessage v-if="errorMessage" class="mt-6" :message="errorMessage" />

    <label class="relative mt-8 block max-w-xl">
      <span class="sr-only">Tìm trong trang hiện tại</span>
      <MagnifyingGlassIcon
        class="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400"
      />
      <input
        v-model.trim="search"
        class="w-full rounded-2xl border border-slate-300 bg-white py-3 pl-12 pr-4"
        placeholder="Tìm theo sản phẩm, seller hoặc shop"
      />
    </label>

    <div class="mt-6 grid gap-5 lg:grid-cols-2">
      <article
        v-for="product in filteredProducts"
        :key="product.id"
        class="overflow-hidden rounded-3xl bg-white shadow-sm ring-1 ring-slate-200"
      >
        <div class="flex gap-4 p-5">
          <img
            v-if="product.thumbnail"
            :src="product.thumbnail"
            :alt="product.name"
            class="h-28 w-28 shrink-0 rounded-2xl bg-slate-100 object-cover"
          />
          <div v-else class="grid h-28 w-28 shrink-0 place-items-center rounded-2xl bg-slate-100">
            <ClockIcon class="h-8 w-8 text-slate-400" />
          </div>
          <div class="min-w-0 flex-1">
            <div class="flex items-start justify-between gap-3">
              <div>
                <span
                  class="inline-flex rounded-full bg-amber-100 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-amber-800"
                >
                  Chờ duyệt
                </span>
                <h2 class="mt-2 line-clamp-2 text-lg font-black">{{ product.name }}</h2>
              </div>
              <button
                class="shrink-0 text-sm font-bold text-indigo-700 hover:underline"
                type="button"
                @click="selected = product"
              >
                Chi tiết
              </button>
            </div>
            <p class="mt-2 text-sm font-bold text-indigo-700">
              {{ formatVnd(product.min_price) }}
              <span v-if="product.max_price !== product.min_price">
                – {{ formatVnd(product.max_price) }}
              </span>
            </p>
            <p class="mt-2 truncate text-xs text-slate-500">{{ product.shop_name }}</p>
          </div>
        </div>
        <div class="flex flex-wrap justify-end gap-2 border-t border-slate-100 bg-slate-50 p-4">
          <button
            class="inline-flex items-center gap-2 rounded-xl border border-rose-200 bg-white px-4 py-2 text-sm font-bold text-rose-700 hover:bg-rose-50 disabled:opacity-50"
            type="button"
            :disabled="actionId === product.id"
            @click="openReject(product)"
          >
            <XMarkIcon class="h-4 w-4" />
            Từ chối
          </button>
          <button
            class="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-bold text-white hover:bg-emerald-700 disabled:opacity-50"
            type="button"
            :disabled="actionId === product.id"
            @click="approve(product)"
          >
            <CheckIcon class="h-4 w-4" />
            Duyệt
          </button>
        </div>
      </article>
    </div>

    <div
      v-if="loading"
      class="mt-6 rounded-3xl bg-white px-6 py-14 text-center text-slate-500 ring-1 ring-slate-200"
    >
      Đang tải hàng chờ duyệt…
    </div>
    <div
      v-else-if="!filteredProducts.length"
      class="mt-6 rounded-3xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center"
    >
      <CheckIcon class="mx-auto h-10 w-10 text-emerald-600" />
      <h2 class="mt-4 text-xl font-black">Hàng chờ đã sạch</h2>
      <p class="mt-2 text-slate-500">Không có sản phẩm nào phù hợp để kiểm duyệt.</p>
    </div>

    <nav v-if="meta.total_pages > 1" class="mt-7 flex justify-end gap-3 text-sm">
      <button
        class="rounded-xl border bg-white px-4 py-2 font-bold disabled:opacity-40"
        :disabled="meta.page <= 1"
        @click="loadProducts(meta.page - 1)"
      >
        Trước
      </button>
      <span class="self-center">Trang {{ meta.page }} / {{ meta.total_pages }}</span>
      <button
        class="rounded-xl border bg-white px-4 py-2 font-bold disabled:opacity-40"
        :disabled="meta.page >= meta.total_pages"
        @click="loadProducts(meta.page + 1)"
      >
        Sau
      </button>
    </nav>

    <div
      v-if="selected"
      class="fixed inset-0 z-40 bg-slate-950/45 backdrop-blur-sm"
      @click="selected = null"
    />
    <aside
      v-if="selected"
      class="fixed inset-y-0 right-0 z-50 w-full max-w-lg overflow-y-auto bg-white p-6 shadow-2xl sm:p-8"
      aria-label="Chi tiết sản phẩm chờ duyệt"
    >
      <div class="flex items-start justify-between gap-4">
        <div>
          <p class="text-xs font-bold uppercase tracking-widest text-indigo-600">
            Hồ sơ kiểm duyệt
          </p>
          <h2 class="mt-2 text-2xl font-black">{{ selected.name }}</h2>
        </div>
        <button
          class="grid h-10 w-10 place-items-center rounded-xl bg-slate-100"
          type="button"
          aria-label="Đóng chi tiết"
          @click="selected = null"
        >
          <XMarkIcon class="h-5 w-5" />
        </button>
      </div>
      <img
        v-if="selected.thumbnail"
        :src="selected.thumbnail"
        :alt="selected.name"
        class="mt-6 aspect-video w-full rounded-2xl bg-slate-100 object-cover"
      />
      <dl class="mt-6 divide-y divide-slate-100 rounded-2xl border border-slate-200 px-4">
        <div class="grid grid-cols-[120px_1fr] gap-3 py-4">
          <dt class="text-sm text-slate-500">Danh mục</dt>
          <dd class="text-sm font-bold">{{ selected.category.name }}</dd>
        </div>
        <div class="grid grid-cols-[120px_1fr] gap-3 py-4">
          <dt class="text-sm text-slate-500">Giá</dt>
          <dd class="text-sm font-bold text-indigo-700">
            {{ formatVnd(selected.min_price) }} – {{ formatVnd(selected.max_price) }}
          </dd>
        </div>
        <div class="grid grid-cols-[120px_1fr] gap-3 py-4">
          <dt class="text-sm text-slate-500">Gian hàng</dt>
          <dd class="text-sm font-bold">{{ selected.shop_name }}</dd>
        </div>
        <div class="grid grid-cols-[120px_1fr] gap-3 py-4">
          <dt class="text-sm text-slate-500">Seller</dt>
          <dd class="text-sm">
            <strong>{{ selected.seller_name || 'Chưa cập nhật tên' }}</strong>
            <span class="mt-1 block text-slate-500">{{ selected.seller_email }}</span>
          </dd>
        </div>
        <div class="grid grid-cols-[120px_1fr] gap-3 py-4">
          <dt class="text-sm text-slate-500">Gửi lúc</dt>
          <dd class="text-sm font-semibold">{{ formatDateTime(selected.created_at) }}</dd>
        </div>
      </dl>
      <div class="mt-7 grid grid-cols-2 gap-3">
        <button
          class="rounded-xl border border-rose-200 px-5 py-3 font-bold text-rose-700"
          type="button"
          @click="openReject(selected)"
        >
          Từ chối
        </button>
        <button
          class="rounded-xl bg-emerald-600 px-5 py-3 font-bold text-white"
          type="button"
          @click="approve(selected)"
        >
          Duyệt sản phẩm
        </button>
      </div>
      <button
        class="mt-3 inline-flex w-full cursor-not-allowed items-center justify-center gap-2 rounded-xl bg-slate-100 px-5 py-3 font-bold text-slate-400"
        type="button"
        disabled
        title="Chỉ sản phẩm đã duyệt mới có thể bị ẩn"
      >
        <EyeSlashIcon class="h-5 w-5" />
        Ẩn vi phạm (khả dụng sau khi duyệt)
      </button>
    </aside>

    <div
      v-if="rejectionTarget"
      class="fixed inset-0 z-[60] grid place-items-center bg-slate-950/55 p-4 backdrop-blur-sm"
      @click.self="rejectionTarget = null"
    >
      <form
        class="w-full max-w-lg rounded-3xl bg-white p-6 shadow-2xl sm:p-8"
        @submit.prevent="reject"
      >
        <h2 class="text-2xl font-black">Từ chối sản phẩm</h2>
        <p class="mt-2 text-sm text-slate-600">
          Nêu rõ vấn đề để seller có thể chỉnh sửa “{{ rejectionTarget.name }}”.
        </p>
        <label class="mt-6 block">
          <span class="text-sm font-bold">Lý do từ chối <span class="text-rose-600">*</span></span>
          <textarea
            v-model.trim="rejectionReason"
            class="mt-2 min-h-32 w-full rounded-xl border border-slate-300 px-3 py-3"
            maxlength="2000"
            required
            autofocus
          />
        </label>
        <div class="mt-6 flex justify-end gap-3">
          <button
            class="rounded-xl border border-slate-300 px-5 py-2.5 font-bold"
            type="button"
            @click="rejectionTarget = null"
          >
            Hủy
          </button>
          <button
            class="rounded-xl bg-rose-600 px-5 py-2.5 font-bold text-white disabled:opacity-50"
            :disabled="!rejectionReason.trim() || Boolean(actionId)"
          >
            Xác nhận từ chối
          </button>
        </div>
      </form>
    </div>
  </main>
</template>
