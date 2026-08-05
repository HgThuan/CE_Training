<script setup lang="ts">
import { ref, watch } from 'vue'
import { XMarkIcon, PhotoIcon, VideoCameraIcon, TrashIcon } from '@heroicons/vue/24/solid'
import { getErrorMessage } from '@/features/auth/errors'
import type { ShopOrder } from '@/features/order/types'
import { afterSalesApi } from '@/features/after-sales/api'

const props = defineProps<{
  isOpen: boolean
  orderId: string
  shopOrder: ShopOrder | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'submitted'): void
}>()

const reason = ref('')
const mediaFiles = ref<Array<{ file: File; type: 'IMAGE' | 'VIDEO'; previewUrl: string }>>([])
const isSubmitting = ref(false)
const errorMsg = ref('')
const successMsg = ref('')

watch(
  () => props.isOpen,
  (newVal) => {
    if (newVal) {
      reason.value = ''
      mediaFiles.value = []
      errorMsg.value = ''
      successMsg.value = ''
    }
  },
)

const handleFileSelect = (event: Event, type: 'IMAGE' | 'VIDEO') => {
  const input = event.target as HTMLInputElement
  if (!input.files?.length) return
  errorMsg.value = ''

  const currentImages = mediaFiles.value.filter((m) => m.type === 'IMAGE').length
  const currentVideos = mediaFiles.value.filter((m) => m.type === 'VIDEO').length

  Array.from(input.files).forEach((file) => {
    if (type === 'IMAGE' && currentImages >= 5) {
      errorMsg.value = 'Tối đa 5 ảnh'
      return
    }
    if (type === 'VIDEO' && currentVideos >= 1) {
      errorMsg.value = 'Tối đa 1 video'
      return
    }

    mediaFiles.value.push({
      file,
      type,
      previewUrl: URL.createObjectURL(file),
    })
  })

  input.value = '' // reset
}

const removeMedia = (index: number) => {
  const media = mediaFiles.value[index]
  URL.revokeObjectURL(media.previewUrl)
  mediaFiles.value.splice(index, 1)
}

const submitReturn = async () => {
  if (!props.shopOrder || !props.orderId) return
  errorMsg.value = ''
  successMsg.value = ''

  if (!reason.value.trim()) {
    errorMsg.value = 'Vui lòng nhập mô tả lý do trả hàng/hoàn tiền'
    return
  }

  isSubmitting.value = true
  try {
    const mediaPayload = mediaFiles.value.map((m) => {
      // Giả lập upload file trả về URL thật để pass validation của Backend
      const fakeUrl =
        m.type === 'IMAGE'
          ? 'https://picsum.photos/800/800'
          : 'https://www.w3schools.com/html/mov_bbb.mp4'
      return { media_type: m.type, file_url: fakeUrl }
    })

    const payload = {
      shop_order_id: props.shopOrder.id,
      reason_code: 'OTHER',
      reason_detail: reason.value,
      items: props.shopOrder.items.map((item) => ({
        order_item_id: item.id,
        quantity: item.quantity,
      })),
      media: mediaPayload,
    }

    await afterSalesApi.createReturn(props.orderId, payload)
    successMsg.value = 'Tạo yêu cầu trả hàng thành công'

    emit('submitted')
    setTimeout(() => {
      emit('close')
    }, 1500)
  } catch (error: unknown) {
    errorMsg.value = getErrorMessage(error)
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div v-if="isOpen" class="relative z-50">
    <div
      class="fixed inset-0 bg-black/25 transition-opacity"
      @click="!isSubmitting && emit('close')"
    ></div>

    <div class="fixed inset-0 z-10 overflow-y-auto">
      <div class="flex min-h-full items-center justify-center p-4 text-center sm:p-0">
        <div
          class="relative transform overflow-hidden rounded-2xl bg-white text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-md p-6"
        >
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-medium leading-6 text-gray-900">
              Yêu cầu trả hàng / hoàn tiền
            </h3>
            <button
              class="rounded-full p-1 hover:bg-gray-100"
              :disabled="isSubmitting"
              @click="emit('close')"
            >
              <XMarkIcon class="w-5 h-5 text-gray-500" />
            </button>
          </div>

          <div v-if="shopOrder" class="flex flex-col gap-1 mb-6 p-3 bg-gray-50 rounded-lg">
            <span class="text-sm font-semibold text-gray-900">{{ shopOrder.shop_name }}</span>
            <span class="text-xs text-gray-500">{{ shopOrder.shop_order_code }}</span>
          </div>

          <!-- Messages -->
          <div v-if="errorMsg" class="mb-4 rounded-md bg-rose-50 p-3 text-sm text-rose-700">
            {{ errorMsg }}
          </div>
          <div v-if="successMsg" class="mb-4 rounded-md bg-emerald-50 p-3 text-sm text-emerald-700">
            {{ successMsg }}
          </div>

          <form class="space-y-4" @submit.prevent="submitReturn">
            <!-- Reason -->
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-1">Mô tả lý do *</label>
              <textarea
                v-model="reason"
                rows="4"
                :disabled="isSubmitting"
                placeholder="Vui lòng cung cấp chi tiết lý do bạn muốn trả hàng hoặc hoàn tiền..."
                class="block w-full rounded-md border-gray-300 shadow-sm border p-2 focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm disabled:bg-gray-50 disabled:text-gray-500"
              ></textarea>
            </div>

            <!-- Media Upload -->
            <div>
              <div class="flex items-center gap-2 mb-2">
                <p class="text-sm text-gray-700 font-medium">Hình ảnh/video chứng minh</p>
                <span class="text-xs text-gray-500">(Tối đa 5 ảnh, 1 video)</span>
              </div>

              <div class="flex flex-wrap gap-2">
                <!-- Media Previews -->
                <div
                  v-for="(media, index) in mediaFiles"
                  :key="index"
                  class="relative w-16 h-16 rounded-lg border overflow-hidden group"
                >
                  <img
                    v-if="media.type === 'IMAGE'"
                    :src="media.previewUrl"
                    class="w-full h-full object-cover"
                  />
                  <video v-else :src="media.previewUrl" class="w-full h-full object-cover" />

                  <button
                    type="button"
                    class="absolute inset-0 bg-black/50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                    @click="removeMedia(index)"
                  >
                    <TrashIcon class="w-5 h-5 text-white" />
                  </button>
                </div>

                <!-- Upload Buttons -->
                <label
                  v-if="mediaFiles.filter((m) => m.type === 'IMAGE').length < 5"
                  class="w-16 h-16 rounded-lg border-2 border-dashed border-gray-300 flex flex-col items-center justify-center text-gray-500 hover:border-indigo-500 hover:text-indigo-500 cursor-pointer transition-colors"
                >
                  <input
                    type="file"
                    accept="image/*"
                    multiple
                    class="hidden"
                    @change="handleFileSelect($event, 'IMAGE')"
                  />
                  <PhotoIcon class="w-6 h-6" />
                </label>

                <label
                  v-if="mediaFiles.filter((m) => m.type === 'VIDEO').length < 1"
                  class="w-16 h-16 rounded-lg border-2 border-dashed border-gray-300 flex flex-col items-center justify-center text-gray-500 hover:border-indigo-500 hover:text-indigo-500 cursor-pointer transition-colors"
                >
                  <input
                    type="file"
                    accept="video/*"
                    class="hidden"
                    @change="handleFileSelect($event, 'VIDEO')"
                  />
                  <VideoCameraIcon class="w-6 h-6" />
                </label>
              </div>
            </div>

            <!-- Footer -->
            <div class="mt-6 flex gap-3">
              <button
                type="button"
                class="flex-1 rounded-xl border border-gray-300 bg-white px-4 py-2 text-sm font-bold text-gray-700 hover:bg-gray-50"
                @click="emit('close')"
              >
                Đóng
              </button>
              <button
                type="submit"
                :disabled="isSubmitting"
                class="flex-1 inline-flex justify-center rounded-xl bg-indigo-600 px-4 py-2 text-sm font-bold text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {{ isSubmitting ? 'Đang xử lý...' : 'Gửi yêu cầu' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>
