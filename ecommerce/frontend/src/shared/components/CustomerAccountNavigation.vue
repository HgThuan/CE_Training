<script setup lang="ts">
import {
  BellIcon,
  BuildingStorefrontIcon,
  ChatBubbleLeftRightIcon,
  ClipboardDocumentListIcon,
  HeartIcon,
  HomeIcon,
  MapPinIcon,
  TicketIcon,
  UserCircleIcon,
} from '@heroicons/vue/24/outline'
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const route = useRoute()

const links = computed(() => [
  { label: 'Tổng quan tài khoản', to: '/account/profile', icon: UserCircleIcon },
  ...(authStore.user?.role === 'customer'
    ? [
        { label: 'Đơn mua', to: '/account/orders', icon: ClipboardDocumentListIcon },
        { label: 'Sổ địa chỉ', to: '/account/addresses', icon: MapPinIcon },
        { label: 'Voucher của tôi', to: '/me/vouchers', icon: TicketIcon },
        { label: 'Sản phẩm yêu thích', to: '/wishlist', icon: HeartIcon },
        { label: 'Tin nhắn', to: '/account/chat', icon: ChatBubbleLeftRightIcon },
        { label: 'Thông báo', to: '/account/notifications', icon: BellIcon },
        { label: 'Đăng ký bán hàng', to: '/account/seller-application', icon: BuildingStorefrontIcon },
      ]
    : []),
])

function isActive(to: string): boolean {
  return route.path === to || route.path.startsWith(`${to}/`)
}
</script>

<template>
  <aside class="customer-account-nav" aria-label="Điều hướng tài khoản">
    <div class="customer-account-nav__heading">
      <span class="customer-account-nav__avatar" aria-hidden="true">
        {{ authStore.user?.full_name?.trim().charAt(0).toUpperCase() || 'M' }}
      </span>
      <span class="min-w-0">
        <span class="block truncate text-sm font-extrabold text-[#0b2a25]">
          {{ authStore.user?.full_name || 'Tài khoản Mercato' }}
        </span>
        <span class="block truncate text-xs text-[#526762]">{{ authStore.user?.email }}</span>
      </span>
    </div>

    <nav class="customer-account-nav__links">
      <RouterLink
        v-for="item in links"
        :key="item.to"
        :to="item.to"
        :class="{ 'customer-account-nav__link--active': isActive(item.to) }"
        class="customer-account-nav__link"
        :aria-current="isActive(item.to) ? 'page' : undefined"
      >
        <component :is="item.icon" class="h-5 w-5 shrink-0" aria-hidden="true" />
        <span>{{ item.label }}</span>
      </RouterLink>
    </nav>

    <RouterLink class="customer-account-nav__home" to="/">
      <HomeIcon class="h-5 w-5" aria-hidden="true" />
      Tiếp tục mua sắm
    </RouterLink>
  </aside>
</template>
