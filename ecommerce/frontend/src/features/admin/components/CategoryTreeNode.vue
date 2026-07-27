<script setup lang="ts">
import {
  Bars3Icon,
  ChevronDownIcon,
  ChevronRightIcon,
  PencilSquareIcon,
  PlusIcon,
  TrashIcon,
} from '@heroicons/vue/24/outline'
import { ref } from 'vue'

import type { Category } from '@/features/product/types'

defineProps<{
  category: Category
  first: boolean
  last: boolean
  busy: boolean
}>()

const emit = defineEmits<{
  edit: [category: Category]
  delete: [category: Category]
  addChild: [category: Category]
  move: [category: Category, direction: number]
  dragStart: [category: Category]
  drop: [category: Category]
}>()

const expanded = ref(true)
</script>

<template>
  <li>
    <div
      class="group flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2.5 shadow-sm transition hover:border-indigo-300"
      draggable="true"
      @dragstart="emit('dragStart', category)"
      @dragover.prevent
      @drop.stop.prevent="emit('drop', category)"
    >
      <button
        class="grid h-8 w-8 place-items-center rounded-lg hover:bg-slate-100 disabled:opacity-30"
        type="button"
        :disabled="!category.children.length"
        :aria-label="expanded ? 'Thu gọn danh mục' : 'Mở rộng danh mục'"
        @click="expanded = !expanded"
      >
        <ChevronDownIcon v-if="expanded && category.children.length" class="h-4 w-4" />
        <ChevronRightIcon v-else class="h-4 w-4" />
      </button>
      <Bars3Icon class="h-5 w-5 cursor-grab text-slate-400" aria-hidden="true" />
      <div class="min-w-0 flex-1">
        <div class="flex flex-wrap items-center gap-2">
          <strong class="truncate text-sm text-slate-950">{{ category.name }}</strong>
          <span
            class="rounded-full px-2 py-0.5 text-[10px] font-bold uppercase"
            :class="
              category.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'
            "
          >
            {{ category.is_active ? 'Hoạt động' : 'Tạm ẩn' }}
          </span>
        </div>
        <p class="mt-0.5 truncate text-xs text-slate-500">{{ category.slug }}</p>
      </div>
      <div
        class="flex items-center gap-1 opacity-100 transition sm:opacity-0 sm:group-hover:opacity-100"
      >
        <button
          class="grid h-8 w-8 place-items-center rounded-lg text-indigo-700 hover:bg-indigo-50"
          type="button"
          :disabled="busy"
          title="Thêm danh mục con"
          @click="emit('addChild', category)"
        >
          <PlusIcon class="h-4 w-4" />
        </button>
        <button
          class="grid h-8 w-8 place-items-center rounded-lg text-slate-700 hover:bg-slate-100"
          type="button"
          :disabled="busy"
          title="Sửa danh mục"
          @click="emit('edit', category)"
        >
          <PencilSquareIcon class="h-4 w-4" />
        </button>
        <button
          class="grid h-8 w-8 place-items-center rounded-lg text-rose-700 hover:bg-rose-50"
          type="button"
          :disabled="busy"
          title="Xóa danh mục"
          @click="emit('delete', category)"
        >
          <TrashIcon class="h-4 w-4" />
        </button>
        <div class="ml-1 flex flex-col">
          <button
            class="h-4 px-1 text-[10px] leading-none text-slate-500 disabled:opacity-20"
            type="button"
            :disabled="first || busy"
            aria-label="Đưa lên"
            @click="emit('move', category, -1)"
          >
            ▲
          </button>
          <button
            class="h-4 px-1 text-[10px] leading-none text-slate-500 disabled:opacity-20"
            type="button"
            :disabled="last || busy"
            aria-label="Đưa xuống"
            @click="emit('move', category, 1)"
          >
            ▼
          </button>
        </div>
      </div>
    </div>
    <ul
      v-if="expanded && category.children.length"
      class="ml-5 space-y-2 border-l border-slate-200 pl-4 pt-2"
    >
      <CategoryTreeNode
        v-for="(child, index) in category.children"
        :key="child.id"
        :category="child"
        :first="index === 0"
        :last="index === category.children.length - 1"
        :busy="busy"
        @edit="emit('edit', $event)"
        @delete="emit('delete', $event)"
        @add-child="emit('addChild', $event)"
        @move="(item, direction) => emit('move', item, direction)"
        @drag-start="emit('dragStart', $event)"
        @drop="emit('drop', $event)"
      />
    </ul>
  </li>
</template>
