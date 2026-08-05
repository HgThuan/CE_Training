<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { XMarkIcon, PhotoIcon, VideoCameraIcon, TrashIcon, StarIcon as StarIconSolid } from '@heroicons/vue/24/solid'
import { StarIcon as StarIconOutline } from '@heroicons/vue/24/outline'

import type { OrderItem } from '@/features/order/types'
import { afterSalesApi } from '@/features/after-sales/api'

const props = defineProps<{
  isOpen: boolean
  orderItem: OrderItem | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'submitted'): void
}>()

const rating = ref(0)
const hoverRating = ref(0)
const content = ref('')
const mediaFiles = ref<Array<{ file?: File, type: 'IMAGE' | 'VIDEO', previewUrl: string, file_url?: string }>>([])
const isSubmitting = ref(false)

const existingReview = computed(() => props.orderItem?.review)
const isEditMode = computed(() => !!existingReview.value)
const isExpired = computed(() => {
  if (!existingReview.value?.editable_until) return false
  return new Date(existingReview.value.editable_until) < new Date()
})

watch(() => props.isOpen, (newVal) => {
  if (newVal) {
    if (existingReview.value) {
      rating.value = existingReview.value.rating
      content.value = existingReview.value.content || ''
      mediaFiles.value = (existingReview.value.media || []).map(m => ({
        type: m.media_type,
        previewUrl: m.file_url,
        file_url: m.file_url
      }))
    } else {
      rating.value = 0
      content.value = ''
      mediaFiles.value = []
    }
  }
})

const handleFileSelect = (event: Event, type: 'IMAGE' | 'VIDEO') => {
  const input = event.target as HTMLInputElement
  if (!input.files?.length) return
  
  const currentImages = mediaFiles.value.filter(m => m.type === 'IMAGE').length
  const currentVideos = mediaFiles.value.filter(m => m.type === 'VIDEO').length
  
  Array.from(input.files).forEach(file => {
    if (type === 'IMAGE' && currentImages >= 5) {
      alert('Tối đa 5 ảnh')
      return
    }
    if (type === 'VIDEO' && currentVideos >= 1) {
      alert('Tối đa 1 video')
      return
    }
    
    mediaFiles.value.push({
      file,
      type,
      previewUrl: URL.createObjectURL(file)
    })
  })
  
  input.value = '' // reset
}

const removeMedia = (index: number) => {
  const media = mediaFiles.value[index]
  if (media.file) {
    URL.revokeObjectURL(media.previewUrl)
  }
  mediaFiles.value.splice(index, 1)
}

const submitReview = async () => {
  if (!props.orderItem) return
  if (rating.value === 0) {
    alert('Vui lòng chọn số sao')
    return
  }

  isSubmitting.value = true
  try {
    // Mock upload for new files
    const mediaPayload = mediaFiles.value.map(m => {
      if (m.file_url) {
        return { media_type: m.type, file_url: m.file_url }
      }
      // Giả lập upload file trả về URL thật để pass validation của Backend
      const fakeUrl = m.type === 'IMAGE' 
        ? 'https://picsum.photos/800/800' 
        : 'https://www.w3schools.com/html/mov_bbb.mp4'
      return { media_type: m.type, file_url: fakeUrl }
    })

    const payload = {
      rating: rating.value,
      content: content.value,
      media: mediaPayload
    }

    if (isEditMode.value && existingReview.value) {
      await afterSalesApi.updateReview(existingReview.value.id, payload)
      alert('Cập nhật đánh giá thành công')
    } else {
      await afterSalesApi.createReview(props.orderItem.id, payload)
      alert('Đã gửi đánh giá thành công')
    }
    
    emit('submitted')
    emit('close')
  } catch (error: any) {
    alert(error.response?.data?.message || 'Có lỗi xảy ra')
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div v-if="isOpen" class="relative z-50">
    <div class="fixed inset-0 bg-black/25 transition-opacity" @click="!isSubmitting && emit('close')"></div>

    <div class="fixed inset-0 z-10 overflow-y-auto">
      <div class="flex min-h-full items-center justify-center p-4 text-center sm:p-0">
        <div class="relative transform overflow-hidden rounded-2xl bg-white text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-md p-6">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-medium leading-6 text-gray-900">
              {{ isEditMode ? 'Đánh giá sản phẩm' : 'Đánh giá sản phẩm' }}
            </h3>
            <button
              @click="emit('close')"
              class="rounded-full p-1 hover:bg-gray-100"
              :disabled="isSubmitting"
            >
              <XMarkIcon class="w-5 h-5 text-gray-500" />
            </button>
          </div>

          <!-- Product Info -->
          <div class="flex items-center gap-3 mb-6 p-3 bg-gray-50 rounded-lg" v-if="orderItem">
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-gray-900 truncate">{{ orderItem?.product_name }}</p>
              <p class="text-xs text-gray-500 truncate">{{ orderItem?.variant_name }}</p>
            </div>
          </div>

          <form @submit.prevent="submitReview" class="space-y-4">
            <!-- Star Rating -->
            <div class="flex flex-col items-center justify-center space-y-2">
              <p class="text-sm text-gray-500">Chất lượng sản phẩm</p>
              <div class="flex gap-1" @mouseleave="hoverRating = 0">
                <button
                  v-for="star in 5"
                  :key="star"
                  type="button"
                  :disabled="isExpired || isSubmitting"
                  class="p-1 focus:outline-none transition-transform hover:scale-110 disabled:hover:scale-100 disabled:cursor-not-allowed"
                  @mouseenter="!isExpired && (hoverRating = star)"
                  @click="!isExpired && (rating = star)"
                >
                  <StarIconSolid
                    v-if="star <= (hoverRating || rating)"
                    class="w-8 h-8 text-yellow-400"
                  />
                  <StarIconOutline
                    v-else
                    class="w-8 h-8 text-gray-300"
                  />
                </button>
              </div>
              <p class="text-xs text-rose-600 h-4 font-medium">{{ isExpired ? 'Đánh giá đã hết hạn chỉnh sửa' : '' }}</p>
            </div>

            <!-- Content -->
            <div>
              <textarea
                v-model="content"
                rows="3"
                :disabled="isExpired || isSubmitting"
                placeholder="Hãy chia sẻ nhận xét của bạn về sản phẩm này nhé..."
                class="block w-full rounded-md border-gray-300 shadow-sm border p-2 focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm disabled:bg-gray-50 disabled:text-gray-500"
              ></textarea>
            </div>

            <!-- Media Upload -->
            <div>
              <div class="flex items-center gap-2 mb-2">
                <p class="text-sm text-gray-700 font-medium">Thêm ảnh/video</p>
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
                  <video 
                    v-else 
                    :src="media.previewUrl"
                    class="w-full h-full object-cover"
                  />
                  
                  <button
                    v-if="!isExpired"
                    type="button"
                    @click="removeMedia(index)"
                    class="absolute inset-0 bg-black/50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <TrashIcon class="w-5 h-5 text-white" />
                  </button>
                </div>

                <!-- Upload Buttons -->
                <label 
                  v-if="!isExpired && mediaFiles.filter(m => m.type === 'IMAGE').length < 5"
                  class="w-16 h-16 rounded-lg border-2 border-dashed border-gray-300 flex flex-col items-center justify-center text-gray-500 hover:border-indigo-500 hover:text-indigo-500 cursor-pointer transition-colors"
                >
                  <input type="file" accept="image/*" multiple class="hidden" @change="handleFileSelect($event, 'IMAGE')" />
                  <PhotoIcon class="w-6 h-6" />
                </label>

                <label 
                  v-if="!isExpired && mediaFiles.filter(m => m.type === 'VIDEO').length < 1"
                  class="w-16 h-16 rounded-lg border-2 border-dashed border-gray-300 flex flex-col items-center justify-center text-gray-500 hover:border-indigo-500 hover:text-indigo-500 cursor-pointer transition-colors"
                >
                  <input type="file" accept="video/*" class="hidden" @change="handleFileSelect($event, 'VIDEO')" />
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
                v-if="!isExpired"
                type="submit"
                :disabled="isSubmitting"
                class="flex-1 inline-flex justify-center rounded-xl bg-indigo-600 px-4 py-2 text-sm font-bold text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                {{ isSubmitting ? 'Đang xử lý...' : (isEditMode ? 'Cập nhật' : 'Gửi đánh giá') }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>
