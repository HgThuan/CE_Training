<script setup lang="ts">
import {
  MagnifyingGlassIcon,
  PencilSquareIcon,
  PlusIcon,
  TrashIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'
import { computed, onMounted, reactive, ref } from 'vue'

import FormMessage from '@/features/auth/components/FormMessage.vue'
import { getErrorMessage } from '@/features/auth/errors'
import type { Brand, BrandPayload } from '@/features/product/types'
import { formatDateTime } from '@/shared/lib/formatters'

import { adminCatalogApi } from '../api'

const brands = ref<Brand[]>([])
const search = ref('')
const loading = ref(true)
const busy = ref(false)
const modalOpen = ref(false)
const editingId = ref('')
const form = reactive({
  name: '',
  slug: '',
  logoUrl: '',
  description: '',
  isActive: true,
})
const message = ref('')
const errorMessage = ref('')

const filteredBrands = computed(() => {
  const query = search.value.trim().toLocaleLowerCase('vi')
  if (!query) return brands.value
  return brands.value.filter((brand) =>
    [brand.name, brand.slug, brand.description].join(' ').toLocaleLowerCase('vi').includes(query),
  )
})

async function loadBrands(): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  try {
    brands.value = (await adminCatalogApi.brands()).data.data
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
}

function openCreate(): void {
  editingId.value = ''
  Object.assign(form, {
    name: '',
    slug: '',
    logoUrl: '',
    description: '',
    isActive: true,
  })
  modalOpen.value = true
}

function openEdit(brand: Brand): void {
  editingId.value = brand.id
  Object.assign(form, {
    name: brand.name,
    slug: brand.slug,
    logoUrl: brand.logo_url ?? '',
    description: brand.description ?? '',
    isActive: brand.is_active,
  })
  modalOpen.value = true
}

async function saveBrand(): Promise<void> {
  busy.value = true
  message.value = ''
  errorMessage.value = ''
  const payload: BrandPayload = {
    name: form.name.trim(),
    slug: form.slug.trim() || undefined,
    logo_url: form.logoUrl.trim() || null,
    description: form.description.trim() || null,
    is_active: form.isActive,
  }
  try {
    const response = editingId.value
      ? await adminCatalogApi.updateBrand(editingId.value, payload)
      : await adminCatalogApi.createBrand(payload)
    message.value = response.data.message
    modalOpen.value = false
    await loadBrands()
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    busy.value = false
  }
}

async function deleteBrand(brand: Brand): Promise<void> {
  if (!window.confirm(`Xóa mềm thương hiệu “${brand.name}”?`)) return
  busy.value = true
  message.value = ''
  errorMessage.value = ''
  try {
    message.value = (await adminCatalogApi.deleteBrand(brand.id)).data.message
    await loadBrands()
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    busy.value = false
  }
}

onMounted(loadBrands)
</script>

<template>
  <main class="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:py-10">
    <div class="flex flex-wrap items-end justify-between gap-5">
      <div>
        <p class="text-sm font-bold uppercase tracking-[0.2em] text-indigo-600">ADM-16</p>
        <h1 class="mt-2 text-3xl font-black tracking-tight sm:text-4xl">Quản lý thương hiệu</h1>
        <p class="mt-3 text-slate-600">
          Duy trì thông tin và trạng thái thương hiệu dùng trên catalog.
        </p>
      </div>
      <button
        class="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 font-bold text-white"
        type="button"
        @click="openCreate"
      >
        <PlusIcon class="h-5 w-5" />
        Thêm thương hiệu
      </button>
    </div>

    <FormMessage v-if="message" class="mt-6" :message="message" variant="success" />
    <FormMessage v-if="errorMessage" class="mt-6" :message="errorMessage" />

    <label class="relative mt-8 block max-w-xl">
      <span class="sr-only">Tìm thương hiệu</span>
      <MagnifyingGlassIcon
        class="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400"
      />
      <input
        v-model.trim="search"
        class="w-full rounded-2xl border border-slate-300 bg-white py-3 pl-12 pr-4"
        placeholder="Tìm theo tên, slug hoặc mô tả"
      />
    </label>

    <div class="mt-6 overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-slate-200">
      <div class="overflow-x-auto">
        <table class="w-full min-w-[850px] text-left text-sm">
          <thead class="bg-slate-50 text-xs uppercase tracking-wider text-slate-500">
            <tr>
              <th class="px-5 py-4">Thương hiệu</th>
              <th class="px-4 py-4">Mô tả</th>
              <th class="px-4 py-4">Trạng thái</th>
              <th class="px-4 py-4">Cập nhật</th>
              <th class="px-5 py-4 text-right">Thao tác</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100">
            <tr v-if="loading">
              <td class="px-5 py-12 text-center text-slate-500" colspan="5">
                Đang tải thương hiệu…
              </td>
            </tr>
            <tr v-else-if="!filteredBrands.length">
              <td class="px-5 py-12 text-center text-slate-500" colspan="5">
                Không có thương hiệu phù hợp.
              </td>
            </tr>
            <tr v-for="brand in filteredBrands" :key="brand.id" class="hover:bg-slate-50">
              <td class="px-5 py-4">
                <div class="flex items-center gap-3">
                  <img
                    v-if="brand.logo_url"
                    :src="brand.logo_url"
                    :alt="brand.name"
                    class="h-12 w-12 rounded-xl bg-white object-contain ring-1 ring-slate-200"
                  />
                  <div
                    v-else
                    class="grid h-12 w-12 place-items-center rounded-xl bg-indigo-50 font-black text-indigo-700"
                  >
                    {{ brand.name.slice(0, 1).toLocaleUpperCase('vi') }}
                  </div>
                  <div>
                    <strong>{{ brand.name }}</strong>
                    <span class="mt-0.5 block text-xs text-slate-500">{{ brand.slug }}</span>
                  </div>
                </div>
              </td>
              <td class="max-w-sm px-4 py-4 text-slate-600">
                <p class="line-clamp-2">{{ brand.description || 'Chưa có mô tả' }}</p>
              </td>
              <td class="px-4 py-4">
                <span
                  class="rounded-full px-2.5 py-1 text-xs font-bold"
                  :class="
                    brand.is_active
                      ? 'bg-emerald-100 text-emerald-800'
                      : 'bg-slate-100 text-slate-600'
                  "
                >
                  {{ brand.is_active ? 'Hoạt động' : 'Tạm ẩn' }}
                </span>
              </td>
              <td class="px-4 py-4 text-slate-500">{{ formatDateTime(brand.updated_at) }}</td>
              <td class="px-5 py-4">
                <div class="flex justify-end gap-2">
                  <button
                    class="grid h-9 w-9 place-items-center rounded-lg border border-slate-300 text-slate-700 hover:text-indigo-700"
                    type="button"
                    :disabled="busy"
                    aria-label="Sửa thương hiệu"
                    @click="openEdit(brand)"
                  >
                    <PencilSquareIcon class="h-4 w-4" />
                  </button>
                  <button
                    class="grid h-9 w-9 place-items-center rounded-lg border border-rose-200 text-rose-700 hover:bg-rose-50"
                    type="button"
                    :disabled="busy"
                    aria-label="Xóa thương hiệu"
                    @click="deleteBrand(brand)"
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

    <div
      v-if="modalOpen"
      class="fixed inset-0 z-50 grid place-items-center bg-slate-950/50 p-4 backdrop-blur-sm"
      @click.self="modalOpen = false"
    >
      <form
        class="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-3xl bg-white p-6 shadow-2xl sm:p-8"
        @submit.prevent="saveBrand"
      >
        <div class="flex items-start justify-between">
          <div>
            <p class="text-xs font-bold uppercase tracking-widest text-indigo-600">Thương hiệu</p>
            <h2 class="mt-2 text-2xl font-black">
              {{ editingId ? 'Cập nhật thương hiệu' : 'Tạo thương hiệu mới' }}
            </h2>
          </div>
          <button
            class="grid h-10 w-10 place-items-center rounded-xl bg-slate-100"
            type="button"
            @click="modalOpen = false"
          >
            <XMarkIcon class="h-5 w-5" />
          </button>
        </div>
        <div class="mt-6 grid gap-5 sm:grid-cols-2">
          <label class="sm:col-span-2">
            <span class="text-sm font-bold">Tên thương hiệu *</span>
            <input
              v-model.trim="form.name"
              class="mt-2 w-full rounded-xl border border-slate-300 px-3 py-3"
              maxlength="150"
              required
            />
          </label>
          <label class="sm:col-span-2">
            <span class="text-sm font-bold">Slug</span>
            <input
              v-model.trim="form.slug"
              class="mt-2 w-full rounded-xl border border-slate-300 px-3 py-3"
              maxlength="180"
              placeholder="Tự tạo nếu để trống"
            />
          </label>
          <label class="sm:col-span-2">
            <span class="text-sm font-bold">URL logo</span>
            <input
              v-model.trim="form.logoUrl"
              class="mt-2 w-full rounded-xl border border-slate-300 px-3 py-3"
              type="url"
            />
          </label>
          <label class="sm:col-span-2">
            <span class="text-sm font-bold">Mô tả</span>
            <textarea
              v-model.trim="form.description"
              class="mt-2 min-h-28 w-full rounded-xl border border-slate-300 px-3 py-3"
            />
          </label>
          <label class="flex items-center gap-3 text-sm font-bold sm:col-span-2">
            <input v-model="form.isActive" class="h-5 w-5 accent-indigo-600" type="checkbox" />
            Cho phép hiển thị trên catalog
          </label>
        </div>
        <div class="mt-7 flex justify-end gap-3">
          <button
            class="rounded-xl border border-slate-300 px-5 py-3 font-bold"
            type="button"
            @click="modalOpen = false"
          >
            Hủy
          </button>
          <button
            class="rounded-xl bg-indigo-600 px-5 py-3 font-bold text-white disabled:opacity-50"
            :disabled="busy"
          >
            {{ busy ? 'Đang lưu…' : 'Lưu thương hiệu' }}
          </button>
        </div>
      </form>
    </div>
  </main>
</template>
