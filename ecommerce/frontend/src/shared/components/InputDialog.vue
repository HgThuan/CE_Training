<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  isOpen: boolean
  title: string
  placeholder?: string
  initialValue?: string
  confirmText?: string
  cancelText?: string
  multiline?: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'confirm', value: string): void
}>()

const inputValue = ref('')

watch(
  () => props.isOpen,
  (newVal) => {
    if (newVal) {
      inputValue.value = props.initialValue || ''
    }
  },
)

const handleConfirm = () => {
  emit('confirm', inputValue.value)
}
</script>

<template>
  <div v-if="isOpen" class="relative z-50">
    <div class="fixed inset-0 bg-black/25 transition-opacity" @click="emit('close')"></div>

    <div class="fixed inset-0 z-10 overflow-y-auto">
      <div class="flex min-h-full items-center justify-center p-4 text-center sm:p-0">
        <div
          class="relative transform overflow-hidden rounded-2xl bg-white text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-md p-6"
        >
          <h3 class="text-lg font-medium leading-6 text-gray-900 mb-4">
            {{ title }}
          </h3>

          <form @submit.prevent="handleConfirm">
            <div class="mb-6">
              <textarea
                v-if="multiline"
                v-model="inputValue"
                rows="3"
                :placeholder="placeholder"
                class="block w-full rounded-md border-gray-300 shadow-sm border p-2 focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
              ></textarea>
              <input
                v-else
                v-model="inputValue"
                type="text"
                :placeholder="placeholder"
                class="block w-full rounded-md border-gray-300 shadow-sm border p-2 focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
              />
            </div>

            <div class="flex gap-3 justify-end">
              <button
                type="button"
                class="rounded-xl border border-gray-300 bg-white px-4 py-2 text-sm font-bold text-gray-700 hover:bg-gray-50"
                @click="emit('close')"
              >
                {{ cancelText || 'Hủy' }}
              </button>
              <button
                type="submit"
                class="inline-flex justify-center rounded-xl bg-indigo-600 px-4 py-2 text-sm font-bold text-white hover:bg-indigo-700"
              >
                {{ confirmText || 'Xác nhận' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>
