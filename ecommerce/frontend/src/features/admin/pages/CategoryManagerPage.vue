<script setup lang="ts">
import { PlusIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import { computed, onMounted, reactive, ref } from 'vue'

import FormMessage from '@/features/auth/components/FormMessage.vue'
import { getErrorMessage } from '@/features/auth/errors'
import type { Category, CategoryOption, CategoryPayload } from '@/features/product/types'

import { adminCatalogApi } from '../api'
import {
  buildCategoryTree,
  containsCategory,
  findCategory,
  siblingReorderItems,
} from '../category-tree'
import CategoryTreeNode from '../components/CategoryTreeNode.vue'

const categories = ref<Category[]>([])
const loading = ref(true)
const busy = ref(false)
const dragged = ref<Category | null>(null)
const modalOpen = ref(false)
const editingId = ref('')
const form = reactive({
  name: '',
  slug: '',
  parentId: '',
  imageUrl: '',
  sortOrder: 0,
  isActive: true,
})
const message = ref('')
const errorMessage = ref('')

const tree = computed(() => buildCategoryTree(categories.value))
const categoryOptions = computed(() => {
  const options: CategoryOption[] = []
  const visit = (items: Category[], depth: number): void => {
    for (const item of items) {
      options.push({ id: item.id, name: item.name, depth })
      visit(item.children, depth + 1)
    }
  }
  visit(tree.value, 0)
  return options
})

async function loadCategories(): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  try {
    categories.value = (await adminCatalogApi.categories()).data.data
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
}

function resetForm(parentId = ''): void {
  editingId.value = ''
  Object.assign(form, {
    name: '',
    slug: '',
    parentId,
    imageUrl: '',
    sortOrder: 0,
    isActive: true,
  })
}

function openCreate(parent?: Category): void {
  resetForm(parent?.id ?? '')
  modalOpen.value = true
}

function openEdit(category: Category): void {
  editingId.value = category.id
  Object.assign(form, {
    name: category.name,
    slug: category.slug,
    parentId: category.parent_id ?? '',
    imageUrl: category.image_url ?? '',
    sortOrder: category.sort_order,
    isActive: category.is_active,
  })
  modalOpen.value = true
}

async function saveCategory(): Promise<void> {
  busy.value = true
  message.value = ''
  errorMessage.value = ''
  const payload: CategoryPayload = {
    name: form.name.trim(),
    slug: form.slug.trim() || undefined,
    parent: form.parentId || null,
    image_url: form.imageUrl.trim() || null,
    sort_order: form.sortOrder,
    is_active: form.isActive,
  }
  try {
    const response = editingId.value
      ? await adminCatalogApi.updateCategory(editingId.value, payload)
      : await adminCatalogApi.createCategory(payload)
    message.value = response.data.message
    modalOpen.value = false
    await loadCategories()
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    busy.value = false
  }
}

async function deleteCategory(category: Category): Promise<void> {
  if (!window.confirm(`Xóa mềm danh mục “${category.name}”?`)) return
  busy.value = true
  message.value = ''
  errorMessage.value = ''
  try {
    message.value = (await adminCatalogApi.deleteCategory(category.id)).data.message
    await loadCategories()
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    busy.value = false
  }
}

async function moveCategory(category: Category, direction: number): Promise<void> {
  const parent = category.parent_id ? findCategory(tree.value, category.parent_id) : null
  const siblings = [...(parent?.children ?? tree.value)]
  const index = siblings.findIndex((item) => item.id === category.id)
  const targetIndex = index + direction
  if (index < 0 || targetIndex < 0 || targetIndex >= siblings.length) return
  const [item] = siblings.splice(index, 1)
  if (item) siblings.splice(targetIndex, 0, item)
  busy.value = true
  try {
    await adminCatalogApi.reorderCategories(siblingReorderItems(siblings))
    await loadCategories()
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    busy.value = false
  }
}

function startDrag(category: Category): void {
  dragged.value = category
}

async function dropOn(target: Category): Promise<void> {
  const source = dragged.value
  dragged.value = null
  if (!source || source.id === target.id) return
  if (containsCategory(source, target.id)) {
    errorMessage.value = 'Không thể chuyển một danh mục vào chính nhánh con của nó.'
    return
  }
  busy.value = true
  try {
    await adminCatalogApi.reorderCategories([
      { id: source.id, parent_id: target.id, sort_order: target.children.length },
    ])
    message.value = `Đã chuyển “${source.name}” vào “${target.name}”.`
    await loadCategories()
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    busy.value = false
  }
}

async function dropAtRoot(): Promise<void> {
  const source = dragged.value
  dragged.value = null
  if (!source) return
  busy.value = true
  try {
    await adminCatalogApi.reorderCategories([
      { id: source.id, parent_id: null, sort_order: tree.value.length },
    ])
    await loadCategories()
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    busy.value = false
  }
}

onMounted(loadCategories)
</script>

<template>
  <main class="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:py-10">
    <div class="flex flex-wrap items-end justify-between gap-5">
      <div>
        <p class="text-sm font-bold uppercase tracking-[0.2em] text-indigo-600">ADM-15</p>
        <h1 class="mt-2 text-3xl font-black tracking-tight sm:text-4xl">Cây danh mục</h1>
        <p class="mt-3 text-slate-600">
          Kéo một danh mục lên danh mục khác để đổi nhánh, hoặc dùng nút lên/xuống để sắp xếp.
        </p>
      </div>
      <button
        class="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 font-bold text-white"
        type="button"
        @click="openCreate()"
      >
        <PlusIcon class="h-5 w-5" />
        Thêm danh mục
      </button>
    </div>

    <FormMessage v-if="message" class="mt-6" :message="message" variant="success" />
    <FormMessage v-if="errorMessage" class="mt-6" :message="errorMessage" />

    <section class="mt-8 rounded-3xl bg-slate-50 p-4 ring-1 ring-slate-200 sm:p-6">
      <div
        class="mb-4 rounded-xl border-2 border-dashed border-slate-300 px-4 py-3 text-center text-xs font-bold text-slate-500 transition hover:border-indigo-400 hover:bg-indigo-50"
        @dragover.prevent
        @drop.prevent="dropAtRoot"
      >
        Thả tại đây để chuyển danh mục về cấp gốc
      </div>
      <p v-if="loading" class="py-12 text-center text-slate-500">Đang tải cây danh mục…</p>
      <p v-else-if="!tree.length" class="py-12 text-center text-slate-500">
        Chưa có danh mục. Hãy tạo nút gốc đầu tiên.
      </p>
      <ul v-else class="space-y-2">
        <CategoryTreeNode
          v-for="(category, index) in tree"
          :key="category.id"
          :category="category"
          :first="index === 0"
          :last="index === tree.length - 1"
          :busy="busy"
          @edit="openEdit"
          @delete="deleteCategory"
          @add-child="openCreate"
          @move="moveCategory"
          @drag-start="startDrag"
          @drop="dropOn"
        />
      </ul>
    </section>

    <div
      v-if="modalOpen"
      class="fixed inset-0 z-50 grid place-items-center bg-slate-950/50 p-4 backdrop-blur-sm"
      @click.self="modalOpen = false"
    >
      <form
        class="max-h-[90vh] w-full max-w-xl overflow-y-auto rounded-3xl bg-white p-6 shadow-2xl sm:p-8"
        @submit.prevent="saveCategory"
      >
        <div class="flex items-start justify-between">
          <div>
            <p class="text-xs font-bold uppercase tracking-widest text-indigo-600">Danh mục</p>
            <h2 class="mt-2 text-2xl font-black">
              {{ editingId ? 'Cập nhật danh mục' : 'Tạo danh mục mới' }}
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
            <span class="text-sm font-bold">Tên danh mục *</span>
            <input
              v-model.trim="form.name"
              class="mt-2 w-full rounded-xl border border-slate-300 px-3 py-3"
              maxlength="150"
              required
            />
          </label>
          <label>
            <span class="text-sm font-bold">Slug</span>
            <input
              v-model.trim="form.slug"
              class="mt-2 w-full rounded-xl border border-slate-300 px-3 py-3"
              maxlength="180"
              placeholder="Tự tạo nếu để trống"
            />
          </label>
          <label>
            <span class="text-sm font-bold">Danh mục cha</span>
            <select
              v-model="form.parentId"
              class="mt-2 w-full rounded-xl border border-slate-300 bg-white px-3 py-3"
            >
              <option value="">Cấp gốc</option>
              <option
                v-for="option in categoryOptions.filter((item) => item.id !== editingId)"
                :key="option.id"
                :value="option.id"
              >
                {{ `${'— '.repeat(option.depth)}${option.name}` }}
              </option>
            </select>
          </label>
          <label class="sm:col-span-2">
            <span class="text-sm font-bold">URL hình ảnh</span>
            <input
              v-model.trim="form.imageUrl"
              class="mt-2 w-full rounded-xl border border-slate-300 px-3 py-3"
              type="url"
            />
          </label>
          <label>
            <span class="text-sm font-bold">Thứ tự</span>
            <input
              v-model.number="form.sortOrder"
              class="mt-2 w-full rounded-xl border border-slate-300 px-3 py-3"
              type="number"
              min="0"
            />
          </label>
          <label class="flex items-end gap-3 pb-3 text-sm font-bold">
            <input v-model="form.isActive" class="h-5 w-5 accent-indigo-600" type="checkbox" />
            Đang hoạt động
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
            {{ busy ? 'Đang lưu…' : 'Lưu danh mục' }}
          </button>
        </div>
      </form>
    </div>
  </main>
</template>
