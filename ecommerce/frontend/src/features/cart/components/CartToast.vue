<script setup lang="ts">
import { CheckCircleIcon, ShoppingBagIcon, XCircleIcon } from '@heroicons/vue/24/solid'
import { XMarkIcon } from '@heroicons/vue/24/outline'

import { formatVnd } from '@/shared/lib/formatters'

import { useCartToast } from '../composables/useCartToast'

const { visible, toastData, hide } = useCartToast()
</script>

<template>
  <Transition
    enter-active-class="transition duration-300 ease-out motion-reduce:transition-none"
    enter-from-class="translate-y-2 opacity-0 sm:translate-x-2 sm:translate-y-0 motion-reduce:translate-x-0 motion-reduce:translate-y-0"
    enter-to-class="translate-x-0 translate-y-0 opacity-100"
    leave-active-class="transition duration-150 ease-in motion-reduce:transition-none"
    leave-from-class="opacity-100"
    leave-to-class="opacity-0"
  >
    <aside
      v-if="visible && toastData"
      class="pointer-events-auto fixed bottom-20 right-4 z-[70] w-[calc(100vw-2rem)] max-w-sm overflow-hidden rounded-2xl bg-[#fffdf8] text-[#0b2a25] shadow-[0_18px_48px_rgba(11,42,37,0.2)] sm:bottom-auto sm:right-6 sm:top-24"
      :role="toastData.status === 'error' ? 'alert' : 'status'"
      :aria-live="toastData.status === 'error' ? 'assertive' : 'polite'"
      aria-atomic="true"
      data-testid="cart-toast"
    >
      <div class="flex items-start gap-3 p-4">
        <CheckCircleIcon
          v-if="toastData.status === 'success'"
          class="size-6 shrink-0 text-emerald-700"
          aria-hidden="true"
        />
        <XCircleIcon v-else class="size-6 shrink-0 text-rose-700" aria-hidden="true" />

        <div class="min-w-0 flex-1">
          <p class="text-sm font-black">
            {{
              toastData.status === 'success'
                ? 'Đã thêm vào giỏ hàng'
                : 'Không thể thêm vào giỏ hàng'
            }}
          </p>
          <p v-if="toastData.status === 'error'" class="mt-1 text-sm leading-5 text-[#526762]">
            {{ toastData.message || 'Vui lòng thử lại sau.' }}
          </p>

          <div v-if="toastData.status === 'success' && toastData.item" class="mt-3 flex gap-3">
            <img
              v-if="toastData.item.image"
              :src="toastData.item.image"
              :alt="toastData.item.product_name"
              class="size-16 shrink-0 rounded-xl bg-[#e8eee9] object-cover"
              loading="lazy"
              decoding="async"
            />
            <span
              v-else
              class="grid size-16 shrink-0 place-items-center rounded-xl bg-[#e8eee9] text-[#526762]"
              aria-hidden="true"
            >
              <ShoppingBagIcon class="size-6" />
            </span>
            <div class="min-w-0 flex-1">
              <p class="truncate text-sm font-bold">{{ toastData.item.product_name }}</p>
              <p v-if="toastData.item.variant_name" class="mt-0.5 truncate text-xs text-[#526762]">
                {{ toastData.item.variant_name }}
              </p>
              <p class="mt-1 text-xs text-[#526762]">Số lượng: {{ toastData.item.quantity }}</p>
              <p class="mt-1 text-sm font-black text-[#c8452d]">
                {{ formatVnd(toastData.item.price) }}
              </p>
            </div>
          </div>

          <div v-if="toastData.status === 'success'" class="mt-4 grid grid-cols-2 gap-2">
            <button
              class="min-h-11 rounded-xl bg-[#e8eee9] px-3 py-2 text-xs font-bold text-[#173b35] transition hover:bg-[#d8e5e0] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#173b35]"
              type="button"
              @click="hide"
            >
              Tiếp tục mua
            </button>
            <RouterLink
              class="inline-flex min-h-11 items-center justify-center rounded-xl bg-[#e85d3f] px-3 py-2 text-center text-xs font-bold text-white transition hover:bg-[#c8452d] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#c8452d]"
              to="/cart"
              @click="hide"
            >
              Xem giỏ hàng
            </RouterLink>
          </div>
        </div>

        <button
          class="grid size-11 shrink-0 place-items-center rounded-xl text-[#526762] transition hover:bg-[#e8eee9] hover:text-[#173b35] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#173b35]"
          type="button"
          aria-label="Đóng thông báo giỏ hàng"
          @click="hide"
        >
          <XMarkIcon class="size-5" aria-hidden="true" />
        </button>
      </div>
    </aside>
  </Transition>
</template>
