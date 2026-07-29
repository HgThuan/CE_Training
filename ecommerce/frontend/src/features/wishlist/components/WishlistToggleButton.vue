<script setup lang="ts">
import { HeartIcon } from '@heroicons/vue/24/outline'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { getErrorMessage } from '@/features/auth/errors'
import { useAuthStore } from '@/stores/auth'

import { useWishlistStore } from '../store'

const props = withDefaults(
  defineProps<{
    productId: string
    productName: string
    variant?: 'overlay' | 'inline'
  }>(),
  { variant: 'inline' },
)

const emit = defineEmits<{
  toggled: [isWishlisted: boolean]
}>()

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const wishlistStore = useWishlistStore()
const statusMessage = ref('')

const isWishlisted = computed(() => wishlistStore.isWishlisted(props.productId))
const pending = computed(() => wishlistStore.isPending(props.productId))
const isWrongRole = computed(() => Boolean(authStore.user && authStore.user.role !== 'customer'))
const label = computed(() =>
  isWishlisted.value
    ? `Bỏ ${props.productName} khỏi danh sách yêu thích`
    : `Thêm ${props.productName} vào danh sách yêu thích`,
)

async function toggle(): Promise<void> {
  statusMessage.value = ''
  if (!authStore.user) {
    await router.push({
      name: 'login',
      query: { redirect: route.fullPath },
    })
    return
  }
  if (authStore.user.role !== 'customer') {
    statusMessage.value = 'Chỉ tài khoản Customer có thể dùng wishlist.'
    return
  }
  try {
    const result = await wishlistStore.toggle(props.productId)
    statusMessage.value = result.is_wishlisted
      ? 'Đã thêm vào danh sách yêu thích.'
      : 'Đã bỏ khỏi danh sách yêu thích.'
    emit('toggled', result.is_wishlisted)
  } catch (error) {
    statusMessage.value = getErrorMessage(error)
  }
}

watch(
  () => [authStore.user?.id, authStore.user?.role] as const,
  ([, role]) => {
    if (role === 'customer') {
      void wishlistStore.hydrateMembership().catch((error: unknown) => {
        statusMessage.value = getErrorMessage(error)
      })
    }
  },
  { immediate: true },
)
</script>

<template>
  <button
    class="grid min-h-11 min-w-11 place-items-center rounded-full transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 disabled:cursor-not-allowed disabled:opacity-50"
    :class="
      variant === 'overlay'
        ? 'bg-white/95 text-slate-700 shadow-lg backdrop-blur hover:text-rose-600'
        : 'border border-slate-300 bg-white text-slate-700 hover:border-rose-300 hover:text-rose-600'
    "
    type="button"
    :aria-label="label"
    :aria-pressed="isWishlisted"
    :aria-busy="pending"
    :disabled="pending || isWrongRole"
    :title="isWrongRole ? 'Chỉ Customer có thể dùng wishlist' : label"
    @click.stop="toggle"
  >
    <HeartIcon
      class="h-5 w-5"
      :class="isWishlisted ? 'fill-rose-500 text-rose-500' : ''"
      aria-hidden="true"
    />
    <span class="sr-only" aria-live="polite">{{ statusMessage }}</span>
  </button>
</template>
