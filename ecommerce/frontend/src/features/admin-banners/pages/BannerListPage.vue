<script setup lang="ts">
import {
  ArrowDownIcon,
  ArrowUpIcon,
  Bars3Icon,
  PencilSquareIcon,
  PhotoIcon,
  PlusIcon,
  TrashIcon,
} from '@heroicons/vue/24/outline'
import { computed, onMounted, ref } from 'vue'

import FormMessage from '@/features/auth/components/FormMessage.vue'
import { getErrorMessage } from '@/features/auth/errors'
import ConfirmDialog from '@/shared/components/ConfirmDialog.vue'
import { formatDateTime } from '@/shared/lib/formatters'

import { adminBannersApi } from '../api'
import { bannersForPosition, moveBanner as moveBannerInList, reorderBanners } from '../banner-order'
import { BANNER_POSITIONS, type Banner } from '../types'

const banners = ref<Banner[]>([])
const loading = ref(true)
const busy = ref(false)
const draggedId = ref('')
const message = ref('')
const errorMessage = ref('')
const showDeleteDialog = ref(false)
const bannerToDelete = ref<Banner | null>(null)

const positionLabels: Record<Banner['position'], string> = {
  hero: 'Đầu trang',
  middle: 'Giữa trang',
}

const groups = computed(() =>
  BANNER_POSITIONS.map((position) => ({
    position,
    label: positionLabels[position],
    banners: bannersForPosition(banners.value, position),
  })),
)

async function loadBanners(): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  try {
    banners.value = (await adminBannersApi.list()).data.data
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
}

async function swapBanners(sourceId: string, targetId: string): Promise<void> {
  if (!reorderBanners(banners.value, sourceId, targetId)) {
    errorMessage.value = 'Chỉ có thể sắp xếp banner trong cùng một vị trí hiển thị.'
    return
  }
  busy.value = true
  message.value = ''
  errorMessage.value = ''
  try {
    const response = await adminBannersApi.reorder(sourceId, targetId)
    message.value = response.data.message
    await loadBanners()
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    busy.value = false
  }
}

function startDrag(event: DragEvent, banner: Banner): void {
  draggedId.value = banner.id
  event.dataTransfer?.setData('text/plain', banner.id)
  if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move'
}

async function dropOn(target: Banner): Promise<void> {
  const sourceId = draggedId.value
  draggedId.value = ''
  if (!sourceId || sourceId === target.id) return
  await swapBanners(sourceId, target.id)
}

async function moveBanner(banner: Banner, direction: -1 | 1): Promise<void> {
  const reordered = moveBannerInList(banners.value, banner.id, direction)
  if (!reordered) return
  const targetIndex = reordered.findIndex((item) => item.id === banner.id) - direction
  const target = reordered[targetIndex]
  if (target) await swapBanners(banner.id, target.id)
}

function requestDeleteBanner(banner: Banner): void {
  bannerToDelete.value = banner
  showDeleteDialog.value = true
}

function cancelDelete(): void {
  showDeleteDialog.value = false
  bannerToDelete.value = null
}

async function confirmDelete(): Promise<void> {
  const banner = bannerToDelete.value
  if (!banner) return
  showDeleteDialog.value = false
  bannerToDelete.value = null
  busy.value = true
  message.value = ''
  errorMessage.value = ''
  try {
    const response = await adminBannersApi.delete(banner.id)
    message.value = response.data.message
    await loadBanners()
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    busy.value = false
  }
}

function scheduleLabel(banner: Banner): string {
  if (!banner.starts_at && !banner.ends_at) return 'Không giới hạn thời gian'
  const start = banner.starts_at ? formatDateTime(banner.starts_at) : 'Ngay bây giờ'
  const end = banner.ends_at ? formatDateTime(banner.ends_at) : 'Không giới hạn'
  return `${start} → ${end}`
}

onMounted(loadBanners)
</script>

<template>
  <main class="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:py-10">
    <div class="flex flex-wrap items-end justify-between gap-5">
      <div>
        <p class="text-sm font-bold uppercase tracking-[0.2em] text-indigo-600">ADM-21</p>
        <h1 class="mt-2 text-3xl font-black tracking-tight sm:text-4xl">Quản lý banner</h1>
        <p class="mt-3 max-w-2xl text-slate-600">
          Kéo thả hoặc dùng nút lên, xuống để đổi thứ tự banner trong từng vị trí.
        </p>
      </div>
      <RouterLink
        class="inline-flex items-center gap-2 rounded-xl bg-indigo-600 px-5 py-3 font-bold text-white hover:bg-indigo-700"
        to="/admin/banners/new"
      >
        <PlusIcon class="h-5 w-5" />
        Thêm banner
      </RouterLink>
    </div>

    <FormMessage v-if="message" class="mt-6" :message="message" variant="success" />
    <FormMessage v-if="errorMessage" class="mt-6" :message="errorMessage" />

    <div
      v-if="loading"
      class="mt-8 grid gap-5 sm:grid-cols-2 xl:grid-cols-3"
      aria-label="Đang tải banner"
    >
      <div
        v-for="index in 3"
        :key="index"
        class="overflow-hidden rounded-3xl bg-white ring-1 ring-slate-200"
      >
        <div class="aspect-[16/7] animate-pulse bg-slate-200" />
        <div class="space-y-3 p-5">
          <div class="h-5 w-2/3 animate-pulse rounded bg-slate-200" />
          <div class="h-4 animate-pulse rounded bg-slate-100" />
        </div>
      </div>
    </div>

    <div
      v-else-if="!banners.length"
      class="mt-8 rounded-3xl border border-dashed border-slate-300 bg-white px-6 py-16 text-center"
    >
      <PhotoIcon class="mx-auto h-12 w-12 text-slate-400" />
      <h2 class="mt-4 text-xl font-black">Chưa có banner</h2>
      <p class="mt-2 text-slate-600">Tạo banner đầu tiên để làm mới trang chủ.</p>
    </div>

    <div v-else class="mt-8 space-y-10">
      <section v-for="group in groups" :key="group.position">
        <div class="flex items-center justify-between gap-4">
          <div>
            <h2 class="text-xl font-black">{{ group.label }}</h2>
            <p class="mt-1 text-sm text-slate-500">{{ group.banners.length }} banner</p>
          </div>
          <span
            class="rounded-full bg-indigo-50 px-3 py-1 text-xs font-bold uppercase text-indigo-700"
          >
            {{ group.position }}
          </span>
        </div>

        <div v-if="group.banners.length" class="mt-4 grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
          <article
            v-for="(banner, index) in group.banners"
            :key="banner.id"
            class="group overflow-hidden rounded-3xl bg-white shadow-sm ring-1 ring-slate-200 transition hover:shadow-lg"
            :class="draggedId === banner.id ? 'opacity-50 ring-2 ring-indigo-500' : ''"
            draggable="true"
            @dragstart="startDrag($event, banner)"
            @dragend="draggedId = ''"
            @dragover.prevent
            @drop.prevent="dropOn(banner)"
          >
            <div class="relative aspect-[16/7] bg-slate-100">
              <img
                :src="banner.image_url"
                :alt="banner.title || 'Banner trang chủ'"
                class="h-full w-full object-cover"
                loading="lazy"
              />
              <span
                class="absolute left-3 top-3 rounded-full px-2.5 py-1 text-xs font-bold shadow-sm backdrop-blur"
                :class="
                  banner.is_active
                    ? 'bg-emerald-50/95 text-emerald-800'
                    : 'bg-slate-950/75 text-white'
                "
              >
                {{ banner.is_active ? 'Hoạt động' : 'Tạm ẩn' }}
              </span>
            </div>

            <div class="p-5">
              <div class="flex items-start gap-3">
                <Bars3Icon
                  class="mt-0.5 h-5 w-5 shrink-0 cursor-grab text-slate-400"
                  aria-hidden="true"
                />
                <div class="min-w-0 flex-1">
                  <h3 class="truncate font-black">{{ banner.title || 'Không tiêu đề' }}</h3>
                  <p class="mt-1 truncate text-xs text-slate-500">
                    {{ banner.target_url || 'Không có liên kết đích' }}
                  </p>
                </div>
                <span class="text-xs font-bold text-slate-400">#{{ banner.sort_order }}</span>
              </div>

              <p class="mt-4 text-xs leading-5 text-slate-500">{{ scheduleLabel(banner) }}</p>

              <div class="mt-5 flex items-center justify-between gap-3">
                <div class="flex gap-1">
                  <button
                    class="grid h-10 w-10 place-items-center rounded-xl border border-slate-300 text-slate-700 disabled:opacity-30"
                    type="button"
                    :disabled="busy || index === 0"
                    aria-label="Đưa banner lên"
                    @click="moveBanner(banner, -1)"
                  >
                    <ArrowUpIcon class="h-4 w-4" />
                  </button>
                  <button
                    class="grid h-10 w-10 place-items-center rounded-xl border border-slate-300 text-slate-700 disabled:opacity-30"
                    type="button"
                    :disabled="busy || index === group.banners.length - 1"
                    aria-label="Đưa banner xuống"
                    @click="moveBanner(banner, 1)"
                  >
                    <ArrowDownIcon class="h-4 w-4" />
                  </button>
                </div>
                <div class="flex gap-1">
                  <RouterLink
                    class="grid h-10 w-10 place-items-center rounded-xl text-indigo-700 hover:bg-indigo-50"
                    :to="`/admin/banners/${banner.id}/edit`"
                    aria-label="Sửa banner"
                  >
                    <PencilSquareIcon class="h-5 w-5" />
                  </RouterLink>
                  <button
                    class="grid h-10 w-10 place-items-center rounded-xl text-rose-700 hover:bg-rose-50 disabled:opacity-30"
                    type="button"
                    :disabled="busy"
                    aria-label="Xóa banner"
                    @click="requestDeleteBanner(banner)"
                  >
                    <TrashIcon class="h-5 w-5" />
                  </button>
                </div>
              </div>
            </div>
          </article>
        </div>
        <p
          v-else
          class="mt-4 rounded-2xl border border-dashed border-slate-300 bg-white px-5 py-8 text-center text-sm text-slate-500"
        >
          Chưa có banner ở vị trí này.
        </p>
      </section>
    </div>

    <ConfirmDialog
      :open="showDeleteDialog"
      title="Xóa banner"
      :message="`Bạn có chắc chắn muốn xóa banner &quot;${bannerToDelete?.title || 'Không tiêu đề'}&quot;? Thao tác này không thể hoàn tác.`"
      confirm-text="Xóa"
      cancel-text="Hủy"
      variant="danger"
      @confirm="confirmDelete"
      @cancel="cancelDelete"
    />
  </main>
</template>
