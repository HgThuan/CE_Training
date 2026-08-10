<script setup lang="ts">
import { CheckCircleIcon, XCircleIcon } from '@heroicons/vue/24/solid'
import { XMarkIcon } from '@heroicons/vue/24/outline'
import { RouterLink } from 'vue-router'

import { formatVnd } from '@/shared/lib/formatters'
import { useCartToast } from '../composables/useCartToast'

const { showToast, toastData, hide } = useCartToast()
</script>

<template>
  <Transition
    enter-active-class="transform ease-out duration-300 transition"
    enter-from-class="translate-y-2 opacity-0 sm:translate-y-0 sm:translate-x-2"
    enter-to-class="translate-y-0 opacity-100 sm:translate-x-0"
    leave-active-class="transition ease-in duration-100"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <div
      v-if="showToast && toastData"
      class="pointer-events-auto w-[calc(100vw-2rem)] sm:w-96 overflow-hidden rounded-2xl bg-white shadow-xl ring-1 ring-black ring-opacity-5"
    >
      <div class="p-4">
        <div class="flex items-start">
          <div class="shrink-0">
            <CheckCircleIcon v-if="toastData.status === 'success'" class="h-6 w-6 text-emerald-500" aria-hidden="true" />
            <XCircleIcon v-else class="h-6 w-6 text-rose-500" aria-hidden="true" />
          </div>
          <div class="ml-3 w-0 flex-1 pt-0.5">
            <p class="text-sm font-bold text-slate-900">
              {{ toastData.status === 'success' ? 'Thêm vào giỏ hàng thành công!' : 'Thêm vào giỏ hàng thất bại' }}
            </p>
            
            <p v-if="toastData.status === 'error' && toastData.message" class="mt-1 text-sm text-slate-500">
              {{ toastData.message }}
            </p>

            <template v-if="toastData.status === 'success' && toastData.item">
              <div class="mt-3 flex gap-3">
                <img
                  v-if="toastData.item.image"
                  :src="toastData.item.image"
                  :alt="toastData.item.product_name"
                  class="h-16 w-16 shrink-0 rounded-lg object-cover bg-slate-100"
                />
                <div class="flex-1 min-w-0">
                  <h4 class="text-sm font-semibold text-slate-900 truncate">{{ toastData.item.product_name }}</h4>
                  <p v-if="toastData.item.variant_name" class="mt-0.5 text-xs text-slate-500 truncate">
                    {{ toastData.item.variant_name }}
                  </p>
                  <p class="mt-0.5 text-xs text-slate-500">
                    Số lượng: {{ toastData.item.quantity }}
                  </p>
                  <p class="mt-0.5 text-sm font-bold text-indigo-700">
                    {{ formatVnd(toastData.item.price) }}
                  </p>
                </div>
              </div>
              
              <div class="mt-4 flex gap-2">
                <button
                  type="button"
                  class="flex-1 rounded-xl bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-200 transition"
                  @click="hide"
                >
                  Tiếp tục mua
                </button>
                <RouterLink
                  to="/cart"
                  class="flex-1 text-center rounded-xl bg-indigo-600 px-3 py-2 text-xs font-semibold text-white hover:bg-indigo-700 transition"
                  @click="hide"
                >
                  Xem giỏ hàng
                </RouterLink>
              </div>
            </template>
          </div>
          <div class="ml-4 flex shrink-0">
            <button
              type="button"
              class="inline-flex rounded-md bg-white text-slate-400 hover:text-slate-500 focus:outline-none"
              @click="hide"
            >
              <span class="sr-only">Đóng</span>
              <XMarkIcon class="h-5 w-5" aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>
