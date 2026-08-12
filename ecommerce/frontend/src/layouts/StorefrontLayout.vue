<script setup lang="ts">
import {
  ArrowLeftStartOnRectangleIcon,
  Bars3Icon,
  HeartIcon,
  ClipboardDocumentListIcon,
  ShoppingBagIcon,
  UserCircleIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterView, useRoute, useRouter } from 'vue-router'

import { homePathForRole } from '@/features/auth/routes'
import SearchBar from '@/features/search/components/SearchBar.vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()
const mobileMenuOpen = ref(false)

const mobileMenuButton = ref<HTMLButtonElement | null>(null)
watch(
  () => route.fullPath,
  () => {
    mobileMenuOpen.value = false
  },
)

function handleKeydown(event: KeyboardEvent): void {
  if (event.key !== 'Escape' || !mobileMenuOpen.value) return
  mobileMenuOpen.value = false
  mobileMenuButton.value?.focus()
}

onMounted(() => window.addEventListener('keydown', handleKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', handleKeydown))

async function logout(): Promise<void> {
  await authStore.logout()
  mobileMenuOpen.value = false
  await router.push('/')
}
</script>

<template>
  <div class="min-h-screen bg-[#f8fafc] text-slate-900">
    <header class="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div class="mx-auto flex max-w-7xl flex-wrap items-center gap-3 px-4 py-3 sm:px-6">
        <RouterLink class="order-1 flex shrink-0 items-center gap-3 font-black" to="/">
          <span class="grid h-10 w-10 place-items-center rounded-2xl bg-indigo-600 text-white"
            >M</span
          >
          <span class="hidden sm:inline">Mercato</span>
        </RouterLink>

        <SearchBar
          class="order-3 basis-full md:order-2 md:mx-3 md:min-w-64 md:flex-1 md:basis-auto"
        />

        <nav
          class="order-3 ml-auto hidden shrink-0 items-center gap-1 text-sm font-bold lg:flex"
          aria-label="Điều hướng cửa hàng"
        >
          <RouterLink
            class="rounded-xl px-3 py-2 text-slate-600 hover:bg-slate-100 hover:text-slate-950"
            to="/"
          >
            Trang chủ
          </RouterLink>
          <RouterLink
            class="inline-flex items-center gap-2 rounded-xl px-3 py-2 text-slate-600 hover:bg-slate-100 hover:text-slate-950"
            to="/products"
          >
            <ShoppingBagIcon class="h-4 w-4" />
            Sản phẩm
          </RouterLink>
          <RouterLink
            v-if="authStore.user?.role === 'customer'"
            class="inline-flex items-center gap-2 rounded-xl px-3 py-2 text-slate-600 hover:bg-slate-100 hover:text-rose-700"
            to="/wishlist"
          >
            <HeartIcon class="h-4 w-4" />
            Yêu thích
          </RouterLink>
          <RouterLink
            v-if="authStore.user?.role === 'customer'"
            class="inline-flex items-center gap-2 rounded-xl px-3 py-2 text-slate-600 hover:bg-indigo-50 hover:text-indigo-700"
            to="/account/orders"
          >
            <ClipboardDocumentListIcon class="h-4 w-4" />
            Đơn hàng
          </RouterLink>
          <RouterLink
            v-if="authStore.user"
            class="inline-flex items-center gap-2 rounded-xl bg-slate-950 px-4 py-2.5 text-white hover:bg-indigo-700"
            :to="homePathForRole(authStore.user.role)"
          >
            <UserCircleIcon class="h-4 w-4" />
            Tài khoản
          </RouterLink>
          <template v-else>
            <RouterLink
              class="rounded-xl px-3 py-2 text-slate-600 hover:bg-slate-100"
              to="/auth/login"
            >
              Đăng nhập
            </RouterLink>
            <RouterLink
              class="rounded-xl bg-slate-950 px-4 py-2.5 text-white hover:bg-indigo-700"
              to="/auth/register"
            >
              Đăng ký
            </RouterLink>
          </template>
          <button
            v-if="authStore.user"
            class="grid h-10 w-10 place-items-center rounded-xl text-slate-500 hover:bg-rose-50 hover:text-rose-700"
            type="button"
            aria-label="Đăng xuất"
            @click="logout"
          >
            <ArrowLeftStartOnRectangleIcon class="h-5 w-5" />
          </button>
        </nav>

        <button
          ref="mobileMenuButton"
          class="order-2 ml-auto grid h-10 w-10 place-items-center rounded-xl border border-slate-300 bg-white lg:hidden"
          type="button"
          :aria-expanded="mobileMenuOpen"
          aria-controls="storefront-mobile-menu"
          :aria-label="mobileMenuOpen ? 'Đóng menu' : 'Mở menu'"
          @click="mobileMenuOpen = !mobileMenuOpen"
        >
          <XMarkIcon v-if="mobileMenuOpen" class="h-5 w-5" />
          <Bars3Icon v-else class="h-5 w-5" />
        </button>
      </div>

      <nav
        v-if="mobileMenuOpen"
        id="storefront-mobile-menu"
        class="border-t border-slate-200 bg-white px-4 py-4 text-sm font-bold shadow-lg sm:px-6 lg:hidden"
        aria-label="Điều hướng cửa hàng trên di động"
      >
        <div class="mx-auto grid max-w-7xl gap-2">
          <RouterLink class="rounded-xl px-4 py-3 hover:bg-slate-100" to="/">Trang chủ</RouterLink>
          <RouterLink class="rounded-xl px-4 py-3 hover:bg-slate-100" to="/products">
            Sản phẩm
          </RouterLink>
          <RouterLink
            v-if="authStore.user?.role === 'customer'"
            class="inline-flex items-center gap-2 rounded-xl px-4 py-3 hover:bg-slate-100"
            to="/wishlist"
          >
            <HeartIcon class="h-5 w-5 text-rose-500" />
            Yêu thích
          </RouterLink>
          <RouterLink
            v-if="authStore.user?.role === 'customer'"
            class="inline-flex items-center gap-2 rounded-xl px-4 py-3 hover:bg-slate-100"
            to="/account/orders"
          >
            <ClipboardDocumentListIcon class="h-5 w-5 text-indigo-500" />
            Đơn hàng của tôi
          </RouterLink>
          <RouterLink
            v-if="authStore.user"
            class="rounded-xl px-4 py-3 hover:bg-slate-100"
            :to="homePathForRole(authStore.user.role)"
          >
            Tài khoản
          </RouterLink>
          <template v-else>
            <RouterLink class="rounded-xl px-4 py-3 hover:bg-slate-100" to="/auth/login">
              Đăng nhập
            </RouterLink>
            <RouterLink class="rounded-xl bg-slate-950 px-4 py-3 text-white" to="/auth/register">
              Đăng ký
            </RouterLink>
          </template>
          <button
            v-if="authStore.user"
            class="rounded-xl px-4 py-3 text-left text-rose-700 hover:bg-rose-50"
            type="button"
            @click="logout"
          >
            Đăng xuất
          </button>
        </div>
      </nav>
    </header>

    <RouterView />
  </div>
</template>
