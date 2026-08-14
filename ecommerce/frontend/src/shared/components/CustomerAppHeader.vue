<script setup lang="ts">
import {
  ArrowLeftStartOnRectangleIcon,
  Bars3Icon,
  ChatBubbleLeftRightIcon,
  ClipboardDocumentListIcon,
  HeartIcon,
  HomeIcon,
  ShoppingBagIcon,
  ShoppingCartIcon,
  TicketIcon,
  UserCircleIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { homePathForRole } from '@/features/auth/routes'
import NotificationBell from '@/features/notification/components/NotificationBell.vue'
import SearchBar from '@/features/search/components/SearchBar.vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()
const menuOpen = ref(false)
const menuButton = ref<HTMLButtonElement | null>(null)

const primaryLinks = [
  { label: 'Trang chủ', to: '/', icon: HomeIcon },
  { label: 'Sản phẩm', to: '/products', icon: ShoppingBagIcon },
  { label: 'Voucher', to: '/voucher-center', icon: TicketIcon },
]

watch(
  () => route.fullPath,
  () => (menuOpen.value = false),
)

function onKeydown(event: KeyboardEvent): void {
  if (event.key !== 'Escape' || !menuOpen.value) return
  menuOpen.value = false
  menuButton.value?.focus()
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))

async function logout(): Promise<void> {
  await authStore.logout()
  await router.push('/')
}
</script>

<template>
  <header class="market-header">
    <div class="market-header__main">
      <RouterLink class="market-wordmark" to="/" aria-label="Mercato — Trang chủ">
        Mercato
      </RouterLink>

      <SearchBar class="market-search" />

      <div class="market-utilities">
        <RouterLink
          v-if="authStore.user?.role === 'customer'"
          class="market-icon-link"
          to="/wishlist"
          aria-label="Yêu thích"
        >
          <HeartIcon class="size-5" />
        </RouterLink>
        <RouterLink class="market-icon-link" to="/cart" aria-label="Giỏ hàng">
          <ShoppingCartIcon class="size-5" />
        </RouterLink>
        <NotificationBell v-if="authStore.user?.role === 'customer'" to="/account/notifications" />
        <RouterLink
          v-if="authStore.user?.role === 'customer'"
          class="market-icon-link max-lg:hidden"
          to="/account/chat"
          aria-label="Chat"
        >
          <ChatBubbleLeftRightIcon class="size-5" />
        </RouterLink>
        <RouterLink
          v-if="authStore.user"
          class="market-account-link"
          :to="homePathForRole(authStore.user.role)"
        >
          <UserCircleIcon class="size-5" />
          <span class="max-xl:hidden">Tài khoản</span>
        </RouterLink>
        <RouterLink v-else class="market-account-link" to="/auth/login">
          <UserCircleIcon class="size-5" /><span>Đăng nhập</span>
        </RouterLink>
        <button
          ref="menuButton"
          class="market-menu-button"
          type="button"
          :aria-expanded="menuOpen"
          aria-controls="storefront-mobile-menu"
          :aria-label="menuOpen ? 'Đóng menu' : 'Mở menu'"
          @click="menuOpen = !menuOpen"
        >
          <XMarkIcon v-if="menuOpen" class="size-5" />
          <Bars3Icon v-else class="size-5" />
        </button>
      </div>
    </div>

    <div class="market-header__rail">
      <nav class="market-nav" aria-label="Điều hướng mua sắm">
        <RouterLink v-for="item in primaryLinks" :key="item.to" :to="item.to">
          <component :is="item.icon" class="size-4" />
          {{ item.label }}
        </RouterLink>
        <RouterLink v-if="authStore.user?.role === 'customer'" to="/account/orders">
          <ClipboardDocumentListIcon class="size-4" /> Đơn hàng
        </RouterLink>
      </nav>
      <p class="market-promise">Một giỏ hàng · Nhiều gian hàng · Giá rõ ràng</p>
    </div>

    <nav
      v-if="menuOpen"
      id="storefront-mobile-menu"
      class="market-mobile-menu"
      aria-label="Menu Customer"
    >
      <RouterLink v-for="item in primaryLinks" :key="item.to" :to="item.to">
        <component :is="item.icon" class="size-5" /> {{ item.label }}
      </RouterLink>
      <RouterLink to="/wishlist"><HeartIcon class="size-5" /> Yêu thích</RouterLink>
      <RouterLink to="/account/orders"
        ><ClipboardDocumentListIcon class="size-5" /> Đơn hàng</RouterLink
      >
      <RouterLink to="/account/chat"><ChatBubbleLeftRightIcon class="size-5" /> Chat</RouterLink>
      <RouterLink v-if="!authStore.user" to="/auth/register"
        ><UserCircleIcon class="size-5" /> Đăng ký</RouterLink
      >
      <RouterLink v-if="!authStore.user" to="/auth/login"
        ><UserCircleIcon class="size-5" /> Đăng nhập</RouterLink
      >
      <button v-if="authStore.user" type="button" @click="logout">
        <ArrowLeftStartOnRectangleIcon class="size-5" /> Đăng xuất
      </button>
    </nav>
  </header>

  <nav class="market-bottom-nav" aria-label="Điều hướng nhanh trên di động">
    <RouterLink to="/"><HomeIcon class="size-5" /><span>Trang chủ</span></RouterLink>
    <RouterLink to="/products"><ShoppingBagIcon class="size-5" /><span>Sản phẩm</span></RouterLink>
    <RouterLink to="/cart"><ShoppingCartIcon class="size-5" /><span>Giỏ hàng</span></RouterLink>
    <RouterLink to="/account/orders"
      ><ClipboardDocumentListIcon class="size-5" /><span>Đơn hàng</span></RouterLink
    >
    <RouterLink :to="authStore.user ? homePathForRole(authStore.user.role) : '/auth/login'">
      <UserCircleIcon class="size-5" /><span>Tài khoản</span>
    </RouterLink>
  </nav>
</template>
