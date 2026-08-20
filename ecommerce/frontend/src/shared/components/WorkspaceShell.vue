<script setup lang="ts">
import {
  ArrowLeftStartOnRectangleIcon,
  ArrowTopRightOnSquareIcon,
  Bars3Icon,
  ChevronRightIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { Component } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'

import NotificationBell from '@/features/notification/components/NotificationBell.vue'
import { useAuthStore } from '@/stores/auth'

interface NavigationItem {
  label: string
  to: string
  icon: Component
  exact?: boolean
}

interface NavigationGroup {
  label: string
  items: NavigationItem[]
}

const props = defineProps<{
  description: string
  navigation: NavigationGroup[]
  notificationTo?: string
  profileTo?: string
  workspace: 'admin' | 'seller'
  workspaceLabel: string
}>()

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()
const mobileMenuOpen = ref(false)
const menuButton = ref<HTMLButtonElement | null>(null)
const loggingOut = ref(false)

const displayName = computed(() => authStore.user?.full_name || props.workspaceLabel)
const displayInitial = computed(() => displayName.value.trim().charAt(0).toUpperCase() || 'M')
const allItems = computed(() => props.navigation.flatMap((group) => group.items))

function isActive(item: NavigationItem): boolean {
  return item.exact ? route.path === item.to : route.path === item.to || route.path.startsWith(`${item.to}/`)
}

const currentItem = computed(
  () =>
    [...allItems.value]
      .sort((left, right) => right.to.length - left.to.length)
      .find((item) => isActive(item)) ?? allItems.value[0],
)

watch(
  () => route.fullPath,
  () => {
    mobileMenuOpen.value = false
  },
)

watch(mobileMenuOpen, (open) => {
  document.body.classList.toggle('workspace-menu-open', open)
})

function onKeydown(event: KeyboardEvent): void {
  if (event.key !== 'Escape' || !mobileMenuOpen.value) return
  mobileMenuOpen.value = false
  menuButton.value?.focus()
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  document.body.classList.remove('workspace-menu-open')
})

async function logout(): Promise<void> {
  loggingOut.value = true
  try {
    await authStore.logout()
    await router.replace('/auth/login')
  } finally {
    loggingOut.value = false
  }
}
</script>

<template>
  <div class="workspace-shell" :class="`workspace-shell--${workspace}`">
    <a class="app-skip-link" href="#workspace-main">Đi đến nội dung chính</a>

    <Transition
      enter-active-class="transition-opacity duration-200"
      enter-from-class="opacity-0"
      leave-active-class="transition-opacity duration-200"
      leave-to-class="opacity-0"
    >
      <button
        v-if="mobileMenuOpen"
        type="button"
        class="workspace-backdrop"
        aria-label="Đóng menu điều hướng"
        @click="mobileMenuOpen = false"
      />
    </Transition>

    <aside
      class="workspace-sidebar"
      :class="{ 'workspace-sidebar--open': mobileMenuOpen }"
      :aria-label="`Điều hướng ${workspaceLabel}`"
    >
      <div class="workspace-brand">
        <RouterLink to="/" class="workspace-brand__mark" aria-label="Mercato — Trang chủ">
          M
        </RouterLink>
        <div class="min-w-0 flex-1">
          <p class="workspace-brand__name">Mercato</p>
          <p class="workspace-brand__label">{{ workspaceLabel }}</p>
        </div>
        <button
          type="button"
          class="workspace-icon-button lg:hidden"
          aria-label="Đóng menu"
          @click="mobileMenuOpen = false"
        >
          <XMarkIcon class="h-5 w-5" aria-hidden="true" />
        </button>
      </div>

      <nav class="workspace-navigation">
        <section v-for="group in navigation" :key="group.label || 'overview'">
          <p v-if="group.label" class="workspace-navigation__label">{{ group.label }}</p>
          <div class="space-y-1">
            <RouterLink
              v-for="item in group.items"
              :key="item.to"
              :to="item.to"
              class="workspace-navigation__link"
              :class="{ 'workspace-navigation__link--active': isActive(item) }"
              :aria-current="isActive(item) ? 'page' : undefined"
            >
              <component :is="item.icon" class="h-5 w-5 shrink-0" aria-hidden="true" />
              <span class="min-w-0 flex-1 truncate">{{ item.label }}</span>
              <ChevronRightIcon class="workspace-navigation__chevron" aria-hidden="true" />
            </RouterLink>
          </div>
        </section>
      </nav>

      <div class="workspace-account">
        <component
          :is="profileTo ? RouterLink : 'div'"
          :to="profileTo"
          class="workspace-account__profile"
        >
          <img
            v-if="authStore.user?.avatar_url"
            :src="authStore.user.avatar_url"
            :alt="`Ảnh đại diện của ${displayName}`"
            class="h-10 w-10 rounded-xl object-cover"
          />
          <span v-else class="workspace-account__avatar" aria-hidden="true">
            {{ displayInitial }}
          </span>
          <span class="min-w-0 flex-1">
            <span class="block truncate text-sm font-extrabold text-slate-900">
              {{ displayName }}
            </span>
            <span class="block truncate text-xs text-slate-500">{{ authStore.user?.email }}</span>
          </span>
        </component>
        <button
          type="button"
          class="workspace-account__logout"
          :disabled="loggingOut"
          @click="logout"
        >
          <ArrowLeftStartOnRectangleIcon class="h-5 w-5" aria-hidden="true" />
          {{ loggingOut ? 'Đang đăng xuất…' : 'Đăng xuất' }}
        </button>
      </div>
    </aside>

    <div class="workspace-body">
      <header class="workspace-topbar">
        <button
          ref="menuButton"
          type="button"
          class="workspace-icon-button lg:hidden"
          aria-label="Mở menu điều hướng"
          :aria-expanded="mobileMenuOpen"
          @click="mobileMenuOpen = true"
        >
          <Bars3Icon class="h-5 w-5" aria-hidden="true" />
        </button>

        <div class="min-w-0 flex-1">
          <p class="workspace-topbar__eyebrow">{{ workspaceLabel }}</p>
          <p class="workspace-topbar__title">{{ currentItem?.label }}</p>
        </div>

        <p class="workspace-topbar__description">{{ description }}</p>
        <RouterLink class="workspace-storefront-link" to="/">
          <span>Gian hàng</span>
          <ArrowTopRightOnSquareIcon class="h-4 w-4" aria-hidden="true" />
        </RouterLink>
        <NotificationBell v-if="notificationTo" :to="notificationTo" />
      </header>

      <div id="workspace-main" class="workspace-content" tabindex="-1">
        <RouterView />
      </div>
    </div>
  </div>
</template>
