<script setup lang="ts">
import {
  ArrowLeftIcon,
  ArrowUpTrayIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  FilmIcon,
  PhotoIcon,
  PlusIcon,
  TrashIcon,
} from '@heroicons/vue/24/outline'
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import FormMessage from '@/features/auth/components/FormMessage.vue'
import { getErrorMessage } from '@/features/auth/errors'
import type {
  Category,
  CategoryOption,
  ProductMedia,
  SellerAttribute,
  SellerProductDetail,
  SellerProductPayload,
  VariantUpdatePayload,
} from '@/features/product/types'
import { useProductStore } from '@/features/product/store'

import {
  generateVariantDrafts,
  type PendingMedia,
  type VariantDraft,
  validateMediaFile,
  validateVariantDrafts,
  variantKey,
  variantToDraft,
} from '../product-form'
import { sellerProductApi } from '../product-api'

const route = useRoute()
const router = useRouter()
const productStore = useProductStore()

const routeProductId = computed(() =>
  typeof route.params.productId === 'string' ? route.params.productId : '',
)
const isEditing = computed(() => Boolean(routeProductId.value))
const product = ref<SellerProductDetail | null>(null)
const attributes = ref<SellerAttribute[]>([])
const existingMedia = ref<ProductMedia[]>([])
const pendingMedia = ref<PendingMedia[]>([])
const variantDrafts = ref<VariantDraft[]>([])
const serverVariantsExist = ref(false)
const selectedValueIds = reactive<Record<string, string[]>>({})
const form = reactive({
  name: '',
  categoryId: '',
  brandId: '',
  shortDescription: '',
  description: '',
})
const loading = ref(true)
const saving = ref(false)
const dragging = ref(false)
const message = ref('')
const errorMessage = ref('')
const mediaInput = ref<HTMLInputElement | null>(null)
const skuPrefix = `SKU${Date.now().toString().slice(-6)}`

const editable = computed(
  () => !product.value || ['draft', 'rejected'].includes(product.value.status),
)
const hasServerVariants = computed(
  () => serverVariantsExist.value || Boolean(product.value?.variants.length),
)
const categoryOptions = computed(() => {
  const options: CategoryOption[] = []
  const visit = (categories: Category[], depth: number): void => {
    for (const category of categories) {
      options.push({ id: category.id, name: category.name, depth })
      visit(category.children, depth + 1)
    }
  }
  visit(productStore.categories, 0)
  return options
})
const totalMedia = computed(() => existingMedia.value.length + pendingMedia.value.length)

function hydrateProduct(data: SellerProductDetail): void {
  product.value = data
  Object.assign(form, {
    name: data.name,
    categoryId: data.category.id,
    brandId: data.brand?.id ?? '',
    shortDescription: data.short_description ?? '',
    description: data.description ?? '',
  })
  existingMedia.value = [...data.media].sort((a, b) => a.sort_order - b.sort_order)
  variantDrafts.value = data.variants.map(variantToDraft)
  serverVariantsExist.value = data.variants.length > 0
  for (const attribute of data.attributes) {
    selectedValueIds[attribute.id] = attribute.values.map((value) => value.id)
  }
}

function rebuildVariantMatrix(): void {
  variantDrafts.value = generateVariantDrafts(
    attributes.value,
    selectedValueIds,
    variantDrafts.value,
  )
  variantDrafts.value.forEach((draft, index) => {
    if (!draft.sku) draft.sku = `${skuPrefix}-${String(index + 1).padStart(3, '0')}`
  })
}

function isSelected(attributeId: string, valueId: string): boolean {
  return selectedValueIds[attributeId]?.includes(valueId) ?? false
}

function toggleAttributeValue(attributeId: string, valueId: string): void {
  const values = selectedValueIds[attributeId] ?? []
  selectedValueIds[attributeId] = values.includes(valueId)
    ? values.filter((id) => id !== valueId)
    : [...values, valueId]
  rebuildVariantMatrix()
}

async function addFiles(files: FileList | File[]): Promise<void> {
  errorMessage.value = ''
  for (const file of Array.from(files)) {
    const validation = await validateMediaFile(file)
    if ('error' in validation) {
      errorMessage.value = validation.error
      continue
    }
    pendingMedia.value.push({
      id: crypto.randomUUID(),
      file,
      mediaType: validation.mediaType,
      previewUrl: URL.createObjectURL(file),
    })
  }
}

function handleFileInput(event: Event): void {
  const input = event.target as HTMLInputElement
  if (input.files?.length) void addFiles(input.files)
  input.value = ''
}

function handleDrop(event: DragEvent): void {
  dragging.value = false
  if (event.dataTransfer?.files.length) void addFiles(event.dataTransfer.files)
}

function removePendingMedia(index: number): void {
  const item = pendingMedia.value[index]
  if (item) URL.revokeObjectURL(item.previewUrl)
  pendingMedia.value.splice(index, 1)
}

async function removeExistingMedia(item: ProductMedia): Promise<void> {
  if (!routeProductId.value || !window.confirm('Xóa media này khỏi sản phẩm?')) return
  saving.value = true
  errorMessage.value = ''
  try {
    await sellerProductApi.deleteMedia(routeProductId.value, item.id)
    existingMedia.value = existingMedia.value.filter((media) => media.id !== item.id)
    message.value = 'Đã xóa media sản phẩm.'
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    saving.value = false
  }
}

function moveItem<T>(items: T[], index: number, direction: number): T[] {
  const targetIndex = index + direction
  if (targetIndex < 0 || targetIndex >= items.length) return items
  const next = [...items]
  const [item] = next.splice(index, 1)
  if (item !== undefined) next.splice(targetIndex, 0, item)
  return next
}

function moveExisting(index: number, direction: number): void {
  existingMedia.value = moveItem(existingMedia.value, index, direction)
}

function movePending(index: number, direction: number): void {
  pendingMedia.value = moveItem(pendingMedia.value, index, direction)
}

function buildPayload(): SellerProductPayload {
  return {
    name: form.name.trim(),
    category_id: form.categoryId,
    brand_id: form.brandId || null,
    short_description: form.shortDescription.trim() || null,
    description: form.description.trim() || null,
  }
}

function validateForm(requireVariant: boolean): string | null {
  if (!form.name.trim()) return 'Vui lòng nhập tên sản phẩm.'
  if (!form.categoryId) return 'Vui lòng chọn danh mục.'
  return validateVariantDrafts(variantDrafts.value, requireVariant)
}

function variantPayload(draft: VariantDraft): VariantUpdatePayload {
  return {
    sku: draft.sku.trim(),
    barcode: draft.barcode.trim() || null,
    original_price: draft.originalPrice,
    sale_price: draft.salePrice,
    cost_price: draft.costPrice || null,
    weight_grams: draft.weightGrams ? Number(draft.weightGrams) : undefined,
    is_active: draft.isActive,
  }
}

async function persistMedia(productId: string): Promise<void> {
  for (const item of [...pendingMedia.value]) {
    const response = await sellerProductApi.uploadMedia(productId, item.file, item.mediaType)
    existingMedia.value.push(response.data.data)
    pendingMedia.value = pendingMedia.value.filter((pending) => pending.id !== item.id)
    URL.revokeObjectURL(item.previewUrl)
  }
  const orderedIds = existingMedia.value.map((item) => item.id)
  if (orderedIds.length) await sellerProductApi.reorderMedia(productId, orderedIds)
}

async function persistVariants(productId: string): Promise<void> {
  let drafts = variantDrafts.value
  if (!drafts.length) return
  if (!hasServerVariants.value) {
    const allValueIds = [...new Set(drafts.flatMap((draft) => draft.attributeValueIds))]
    const generated = (await sellerProductApi.generateVariants(productId, allValueIds)).data.data
    const generatedByKey = new Map(
      generated.map((variant) => [
        variantKey(variant.attributes.map((attribute) => attribute.attribute_value_id)),
        variant,
      ]),
    )
    drafts = drafts.map((draft) => ({
      ...draft,
      variantId: generatedByKey.get(draft.key)?.id,
    }))
    variantDrafts.value = drafts
    serverVariantsExist.value = true
  }

  for (const draft of drafts) {
    if (!draft.variantId) throw new Error(`Không ghép được biến thể ${draft.label} với API.`)
    await sellerProductApi.updateVariant(productId, draft.variantId, variantPayload(draft))
  }
}

async function saveProduct(submitAfterSave = false): Promise<void> {
  const validationError = validateForm(submitAfterSave || variantDrafts.value.length > 0)
  if (validationError) {
    errorMessage.value = validationError
    return
  }
  saving.value = true
  message.value = ''
  errorMessage.value = ''
  try {
    let productId = routeProductId.value
    if (productId) {
      await sellerProductApi.update(productId, buildPayload())
    } else {
      const created = (await sellerProductApi.create(buildPayload())).data.data
      productId = created.id
      await router.replace(`/seller/products/${productId}/edit`)
    }

    await persistMedia(productId)
    await persistVariants(productId)

    if (submitAfterSave) {
      message.value = (await sellerProductApi.submit(productId)).data.message
      await router.push('/seller/products')
      return
    }

    const refreshed = (await sellerProductApi.detail(productId)).data.data
    pendingMedia.value.forEach((item) => URL.revokeObjectURL(item.previewUrl))
    pendingMedia.value = []
    hydrateProduct(refreshed)
    message.value = 'Đã lưu toàn bộ thông tin, media và SKU.'
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    const [, attributeResponse] = await Promise.all([
      productStore.loadCatalog(),
      sellerProductApi.attributes(),
    ])
    attributes.value = attributeResponse.data.data
    if (routeProductId.value) {
      hydrateProduct((await sellerProductApi.detail(routeProductId.value)).data.data)
    }
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(() => {
  pendingMedia.value.forEach((item) => URL.revokeObjectURL(item.previewUrl))
})
</script>

<template>
  <main class="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:py-10">
    <RouterLink
      class="inline-flex items-center gap-2 text-sm font-bold text-slate-600 hover:text-indigo-700"
      to="/seller/products"
    >
      <ArrowLeftIcon class="h-4 w-4" />
      Danh sách sản phẩm
    </RouterLink>
    <div class="mt-5 flex flex-wrap items-start justify-between gap-4">
      <div>
        <p class="text-sm font-bold uppercase tracking-[0.2em] text-indigo-600">
          SEL-02 · SEL-03 · SEL-04 · SEL-05
        </p>
        <h1 class="mt-2 text-3xl font-black tracking-tight sm:text-4xl">
          {{ isEditing ? 'Chỉnh sửa sản phẩm' : 'Tạo sản phẩm mới' }}
        </h1>
        <p class="mt-3 text-slate-600">
          Hoàn thiện nội dung, media và ma trận SKU trước khi gửi duyệt.
        </p>
      </div>
      <span
        v-if="product"
        class="rounded-full bg-slate-100 px-3 py-1.5 text-xs font-bold uppercase tracking-wider text-slate-700"
      >
        {{ product.status }}
      </span>
    </div>

    <FormMessage v-if="message" class="mt-6" :message="message" variant="success" />
    <FormMessage v-if="errorMessage" class="mt-6" :message="errorMessage" />
    <p v-if="loading" class="mt-10 rounded-2xl bg-white p-8 ring-1 ring-slate-200">
      Đang tải form…
    </p>

    <template v-else>
      <div
        v-if="!editable"
        class="mt-6 rounded-2xl bg-amber-50 p-4 text-sm font-semibold text-amber-900 ring-1 ring-amber-200"
      >
        Sản phẩm đang ở trạng thái <strong>{{ product?.status }}</strong> nên seller chỉ được xem.
      </div>
      <div
        v-if="product?.rejection_reason"
        class="mt-6 rounded-2xl bg-rose-50 p-4 text-sm text-rose-900 ring-1 ring-rose-200"
      >
        <strong>{{ product.status === 'hidden' ? 'Lý do ẩn:' : 'Lý do từ chối:' }}</strong>
        {{ product.rejection_reason }}
      </div>

      <form class="mt-8 space-y-7" @submit.prevent="saveProduct(false)">
        <section class="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200 sm:p-7">
          <div class="flex items-center gap-3">
            <span
              class="grid h-9 w-9 place-items-center rounded-xl bg-indigo-100 font-black text-indigo-700"
              >1</span
            >
            <div>
              <h2 class="text-xl font-black">Thông tin chung</h2>
              <p class="text-sm text-slate-500">Nội dung khách hàng sẽ nhìn thấy trên catalog.</p>
            </div>
          </div>
          <div class="mt-6 grid gap-5 sm:grid-cols-2">
            <label class="sm:col-span-2">
              <span class="text-sm font-bold"
                >Tên sản phẩm <span class="text-rose-600">*</span></span
              >
              <input
                v-model.trim="form.name"
                class="mt-2 w-full rounded-xl border border-slate-300 px-3 py-3 focus:border-indigo-600 focus:outline-none focus:ring-4 focus:ring-indigo-100"
                maxlength="255"
                :disabled="!editable"
                required
              />
            </label>
            <label>
              <span class="text-sm font-bold">Danh mục <span class="text-rose-600">*</span></span>
              <select
                v-model="form.categoryId"
                class="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-3"
                :disabled="!editable"
                required
              >
                <option value="" disabled>Chọn danh mục</option>
                <option v-for="category in categoryOptions" :key="category.id" :value="category.id">
                  {{ `${'— '.repeat(category.depth)}${category.name}` }}
                </option>
              </select>
            </label>
            <label>
              <span class="text-sm font-bold">Thương hiệu</span>
              <select
                v-model="form.brandId"
                class="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-3"
                :disabled="!editable"
              >
                <option value="">Không có thương hiệu</option>
                <option v-for="brand in productStore.brands" :key="brand.id" :value="brand.id">
                  {{ brand.name }}
                </option>
              </select>
            </label>
            <label class="sm:col-span-2">
              <span class="text-sm font-bold">Mô tả ngắn</span>
              <textarea
                v-model.trim="form.shortDescription"
                class="mt-2 min-h-24 w-full rounded-xl border border-slate-300 px-3 py-3"
                :disabled="!editable"
                placeholder="Điểm nổi bật giúp khách hàng hiểu nhanh về sản phẩm"
              />
            </label>
            <label class="sm:col-span-2">
              <span class="text-sm font-bold">Mô tả chi tiết</span>
              <textarea
                v-model.trim="form.description"
                class="mt-2 min-h-48 w-full rounded-xl border border-slate-300 px-3 py-3"
                :disabled="!editable"
                placeholder="Chất liệu, công dụng, hướng dẫn sử dụng, chính sách bảo hành…"
              />
            </label>
          </div>
        </section>

        <section class="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200 sm:p-7">
          <div class="flex items-center gap-3">
            <span
              class="grid h-9 w-9 place-items-center rounded-xl bg-indigo-100 font-black text-indigo-700"
              >2</span
            >
            <div>
              <h2 class="text-xl font-black">Ảnh & video</h2>
              <p class="text-sm text-slate-500">
                JPEG, PNG, WebP tối đa 10 MB; MP4, WebM tối đa 100 MB.
              </p>
            </div>
          </div>

          <button
            class="mt-6 grid w-full place-items-center rounded-2xl border-2 border-dashed px-6 py-10 text-center transition disabled:cursor-not-allowed disabled:opacity-50"
            :class="
              dragging
                ? 'border-indigo-600 bg-indigo-50'
                : 'border-slate-300 bg-slate-50 hover:border-indigo-400 hover:bg-indigo-50/50'
            "
            type="button"
            :disabled="!editable"
            @click="mediaInput?.click()"
            @dragenter.prevent="dragging = true"
            @dragover.prevent="dragging = true"
            @dragleave.prevent="dragging = false"
            @drop.prevent="handleDrop"
          >
            <ArrowUpTrayIcon class="h-9 w-9 text-indigo-600" />
            <strong class="mt-3">Kéo thả hoặc chọn nhiều tệp</strong>
            <span class="mt-1 text-sm text-slate-500"
              >Hệ thống kiểm tra chữ ký tệp trước khi tải lên.</span
            >
          </button>
          <input
            ref="mediaInput"
            class="hidden"
            type="file"
            multiple
            accept="image/jpeg,image/png,image/webp,video/mp4,video/webm"
            @change="handleFileInput"
          />

          <p v-if="!totalMedia" class="mt-5 text-sm text-slate-500">Chưa có media nào.</p>
          <div v-else class="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <article
              v-for="(item, index) in existingMedia"
              :key="item.id"
              class="overflow-hidden rounded-2xl border border-slate-200 bg-white"
            >
              <div class="relative aspect-video bg-slate-100">
                <img
                  v-if="item.media_type === 'image'"
                  :src="item.file_url"
                  :alt="item.alt_text || form.name"
                  class="h-full w-full object-cover"
                />
                <video v-else :src="item.file_url" class="h-full w-full object-cover" muted />
                <span
                  class="absolute left-2 top-2 rounded bg-slate-950/75 px-2 py-1 text-[10px] font-bold text-white"
                >
                  ĐÃ LƯU
                </span>
              </div>
              <div class="flex items-center justify-between p-3">
                <span class="inline-flex items-center gap-1.5 text-xs font-bold text-slate-600">
                  <PhotoIcon v-if="item.media_type === 'image'" class="h-4 w-4" />
                  <FilmIcon v-else class="h-4 w-4" />
                  {{ item.media_type === 'image' ? 'Ảnh' : 'Video' }} {{ index + 1 }}
                </span>
                <div class="flex gap-1">
                  <button
                    class="grid h-8 w-8 place-items-center rounded-lg hover:bg-slate-100 disabled:opacity-30"
                    type="button"
                    :disabled="!editable || index === 0"
                    aria-label="Đưa media lên"
                    @click="moveExisting(index, -1)"
                  >
                    <ChevronUpIcon class="h-4 w-4" />
                  </button>
                  <button
                    class="grid h-8 w-8 place-items-center rounded-lg hover:bg-slate-100 disabled:opacity-30"
                    type="button"
                    :disabled="!editable || index === existingMedia.length - 1"
                    aria-label="Đưa media xuống"
                    @click="moveExisting(index, 1)"
                  >
                    <ChevronDownIcon class="h-4 w-4" />
                  </button>
                  <button
                    class="grid h-8 w-8 place-items-center rounded-lg text-rose-700 hover:bg-rose-50 disabled:opacity-30"
                    type="button"
                    :disabled="!editable || saving"
                    aria-label="Xóa media"
                    @click="removeExistingMedia(item)"
                  >
                    <TrashIcon class="h-4 w-4" />
                  </button>
                </div>
              </div>
            </article>

            <article
              v-for="(item, index) in pendingMedia"
              :key="item.id"
              class="overflow-hidden rounded-2xl border border-indigo-200 bg-indigo-50/30"
            >
              <div class="relative aspect-video bg-slate-100">
                <img
                  v-if="item.mediaType === 'image'"
                  :src="item.previewUrl"
                  :alt="item.file.name"
                  class="h-full w-full object-cover"
                />
                <video v-else :src="item.previewUrl" class="h-full w-full object-cover" muted />
                <span
                  class="absolute left-2 top-2 rounded bg-indigo-600 px-2 py-1 text-[10px] font-bold text-white"
                >
                  CHỜ TẢI
                </span>
              </div>
              <div class="flex items-center justify-between p-3">
                <span class="max-w-36 truncate text-xs font-bold text-slate-600">{{
                  item.file.name
                }}</span>
                <div class="flex gap-1">
                  <button
                    class="grid h-8 w-8 place-items-center rounded-lg hover:bg-white disabled:opacity-30"
                    type="button"
                    :disabled="index === 0"
                    aria-label="Đưa tệp lên"
                    @click="movePending(index, -1)"
                  >
                    <ChevronUpIcon class="h-4 w-4" />
                  </button>
                  <button
                    class="grid h-8 w-8 place-items-center rounded-lg hover:bg-white disabled:opacity-30"
                    type="button"
                    :disabled="index === pendingMedia.length - 1"
                    aria-label="Đưa tệp xuống"
                    @click="movePending(index, 1)"
                  >
                    <ChevronDownIcon class="h-4 w-4" />
                  </button>
                  <button
                    class="grid h-8 w-8 place-items-center rounded-lg text-rose-700 hover:bg-rose-50"
                    type="button"
                    aria-label="Bỏ tệp"
                    @click="removePendingMedia(index)"
                  >
                    <TrashIcon class="h-4 w-4" />
                  </button>
                </div>
              </div>
            </article>
          </div>
        </section>

        <section class="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200 sm:p-7">
          <div class="flex items-center gap-3">
            <span
              class="grid h-9 w-9 place-items-center rounded-xl bg-indigo-100 font-black text-indigo-700"
              >3</span
            >
            <div>
              <h2 class="text-xl font-black">Biến thể & SKU</h2>
              <p class="text-sm text-slate-500">
                Chọn giá trị thuộc tính để tự động sinh mọi tổ hợp.
              </p>
            </div>
          </div>

          <div
            v-if="hasServerVariants"
            class="mt-5 rounded-xl bg-blue-50 px-4 py-3 text-sm font-semibold text-blue-900"
          >
            Ma trận thuộc tính đã được tạo. Bạn vẫn có thể cập nhật SKU, barcode và giá từng dòng.
          </div>
          <div v-else class="mt-6 grid gap-5 md:grid-cols-2">
            <fieldset
              v-for="attribute in attributes"
              :key="attribute.id"
              class="rounded-2xl border border-slate-200 p-4"
              :disabled="!editable"
            >
              <legend class="px-2 text-sm font-black">{{ attribute.name }}</legend>
              <div class="mt-1 flex flex-wrap gap-2">
                <label
                  v-for="value in attribute.values"
                  :key="value.id"
                  class="inline-flex cursor-pointer items-center gap-2 rounded-xl border px-3 py-2 text-sm font-semibold transition"
                  :class="
                    isSelected(attribute.id, value.id)
                      ? 'border-indigo-600 bg-indigo-50 text-indigo-700'
                      : 'border-slate-300 hover:border-slate-500'
                  "
                >
                  <input
                    class="sr-only"
                    type="checkbox"
                    :checked="isSelected(attribute.id, value.id)"
                    @change="toggleAttributeValue(attribute.id, value.id)"
                  />
                  <span
                    v-if="value.color_code"
                    class="h-4 w-4 rounded-full border border-black/10"
                    :style="{ backgroundColor: value.color_code }"
                  />
                  {{ value.display_value || value.value }}
                </label>
              </div>
            </fieldset>
          </div>

          <div
            v-if="variantDrafts.length"
            class="mt-7 overflow-x-auto rounded-2xl border border-slate-200"
          >
            <table class="w-full min-w-[1100px] text-left text-sm">
              <thead class="bg-slate-50 text-xs uppercase tracking-wider text-slate-500">
                <tr>
                  <th class="px-4 py-3">Biến thể</th>
                  <th class="px-3 py-3">SKU *</th>
                  <th class="px-3 py-3">Barcode</th>
                  <th class="px-3 py-3">Giá gốc *</th>
                  <th class="px-3 py-3">Giá bán *</th>
                  <th class="px-3 py-3">Giá vốn</th>
                  <th class="px-3 py-3">Gram</th>
                  <th class="px-3 py-3">Bán</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100">
                <tr v-for="draft in variantDrafts" :key="draft.key">
                  <td class="px-4 py-3 font-bold">{{ draft.label }}</td>
                  <td class="p-2">
                    <input
                      v-model.trim="draft.sku"
                      class="w-36 rounded-lg border border-slate-300 px-2.5 py-2"
                      :disabled="!editable"
                      maxlength="100"
                    />
                  </td>
                  <td class="p-2">
                    <input
                      v-model.trim="draft.barcode"
                      class="w-36 rounded-lg border border-slate-300 px-2.5 py-2"
                      :disabled="!editable"
                      maxlength="100"
                    />
                  </td>
                  <td class="p-2">
                    <input
                      v-model="draft.originalPrice"
                      class="w-32 rounded-lg border border-slate-300 px-2.5 py-2"
                      :disabled="!editable"
                      type="number"
                      min="0"
                      step="1000"
                    />
                  </td>
                  <td class="p-2">
                    <input
                      v-model="draft.salePrice"
                      class="w-32 rounded-lg border border-slate-300 px-2.5 py-2"
                      :disabled="!editable"
                      type="number"
                      min="0"
                      step="1000"
                    />
                  </td>
                  <td class="p-2">
                    <input
                      v-model="draft.costPrice"
                      class="w-32 rounded-lg border border-slate-300 px-2.5 py-2"
                      :disabled="!editable"
                      type="number"
                      min="0"
                      step="1000"
                    />
                  </td>
                  <td class="p-2">
                    <input
                      v-model="draft.weightGrams"
                      class="w-24 rounded-lg border border-slate-300 px-2.5 py-2"
                      :disabled="!editable"
                      type="number"
                      min="1"
                    />
                  </td>
                  <td class="p-2">
                    <input
                      v-model="draft.isActive"
                      class="h-5 w-5 accent-indigo-600"
                      type="checkbox"
                      :disabled="!editable"
                      :aria-label="`Kích hoạt ${draft.label}`"
                    />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div
            v-else
            class="mt-6 rounded-2xl border border-dashed border-slate-300 py-10 text-center text-sm text-slate-500"
          >
            <PlusIcon class="mx-auto h-7 w-7" />
            <p class="mt-2 font-semibold">Chọn ít nhất một giá trị thuộc tính để tạo SKU.</p>
          </div>
        </section>

        <div
          v-if="editable"
          class="sticky bottom-4 z-20 flex flex-wrap justify-end gap-3 rounded-2xl bg-white/95 p-4 shadow-xl ring-1 ring-slate-200 backdrop-blur"
        >
          <RouterLink
            class="rounded-xl border border-slate-300 px-5 py-3 font-bold text-slate-700"
            to="/seller/products"
          >
            Hủy
          </RouterLink>
          <button
            class="rounded-xl border-2 border-indigo-600 px-5 py-3 font-bold text-indigo-700 disabled:opacity-50"
            type="submit"
            :disabled="saving"
          >
            {{ saving ? 'Đang lưu…' : 'Lưu bản nháp' }}
          </button>
          <button
            class="rounded-xl bg-indigo-600 px-5 py-3 font-bold text-white disabled:opacity-50"
            type="button"
            :disabled="saving"
            @click="saveProduct(true)"
          >
            Lưu & gửi duyệt
          </button>
        </div>
      </form>
    </template>
  </main>
</template>
