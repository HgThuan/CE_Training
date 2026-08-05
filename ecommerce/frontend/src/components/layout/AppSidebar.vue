<script setup lang="ts">
import { ArrowLeftStartOnRectangleIcon } from '@heroicons/vue/24/outline'
import { adminNavConfig } from '@/config/nav.config'
import NavGroupComponent from './NavGroup.vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { onMounted, onUnmounted } from 'vue'

const isOpen = defineModel<boolean>('isOpen', { required: true })

const authStore = useAuthStore()
const router = useRouter()

async function logout(): Promise<void> {
  await authStore.logout()
  await router.replace('/auth/login')
}

// Close drawer on escape key
function handleEscape(e: KeyboardEvent) {
  if (e.key === 'Escape' && isOpen.value) {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleEscape)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleEscape)
})
</script>

<template>
  <!-- Mobile drawer -->
  <div
    class="relative z-40 lg:hidden"
    role="dialog"
    aria-modal="true"
    :class="isOpen ? 'pointer-events-auto' : 'pointer-events-none'"
  >
    <!-- Overlay -->
    <transition
      enter-active-class="transition-opacity ease-linear duration-300"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition-opacity ease-linear duration-300"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="isOpen"
        class="fixed inset-0 bg-slate-900/80 backdrop-blur-sm"
        aria-hidden="true"
        @click="isOpen = false"
      ></div>
    </transition>

    <!-- Sidebar content -->
    <transition
      enter-active-class="transition ease-in-out duration-300 transform"
      enter-from-class="-translate-x-full"
      enter-to-class="translate-x-0"
      leave-active-class="transition ease-in-out duration-300 transform"
      leave-from-class="translate-x-0"
      leave-to-class="-translate-x-full"
    >
      <div
        v-if="isOpen"
        class="fixed inset-y-0 left-0 flex w-72 flex-col bg-slate-950 shadow-xl"
      >
        <div class="flex h-16 shrink-0 items-center px-6 border-b border-slate-800">
           <!-- Mobile logo in drawer -->
           <RouterLink class="flex items-center gap-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 rounded-md" to="/admin" @click="isOpen = false">
            <span class="grid h-8 w-8 place-items-center rounded-xl bg-indigo-500 font-black text-white"
              >M</span
            >
            <div>
              <p class="text-[10px] font-bold uppercase tracking-widest text-indigo-300">Mercato</p>
              <p class="text-xs font-black text-white">Admin Console</p>
            </div>
          </RouterLink>
        </div>

        <!-- Scrollable content -->
        <div class="flex grow flex-col overflow-y-auto px-4 py-6">
          <nav class="flex-1 space-y-6">
            <NavGroupComponent
              v-for="(group, index) in adminNavConfig"
              :key="index"
              :group="group"
              @click="isOpen = false"
            />
          </nav>
        </div>
        
        <!-- Logout block -->
        <div class="shrink-0 border-t border-slate-800 p-4">
          <button
            class="group flex w-full items-center gap-3 rounded-xl px-3 py-2 text-sm font-bold text-slate-300 transition-colors hover:bg-rose-500/20 hover:text-rose-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-500"
            type="button"
            @click="logout"
          >
            <ArrowLeftStartOnRectangleIcon class="h-5 w-5 shrink-0" aria-hidden="true" />
            Đăng xuất
          </button>
        </div>
      </div>
    </transition>
  </div>

  <!-- Desktop sidebar -->
  <div class="hidden lg:flex lg:w-64 lg:shrink-0 lg:flex-col lg:bg-slate-950 lg:border-r lg:border-slate-800">
    <div class="flex grow flex-col overflow-y-auto px-4 py-6">
      <nav class="flex-1 space-y-6">
        <NavGroupComponent
          v-for="(group, index) in adminNavConfig"
          :key="index"
          :group="group"
        />
      </nav>
    </div>
    <!-- Logout block -->
    <div class="shrink-0 border-t border-slate-800 p-4">
      <button
        class="group flex w-full items-center gap-3 rounded-xl px-3 py-2 text-sm font-bold text-slate-300 transition-colors hover:bg-rose-500/20 hover:text-rose-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-500"
        type="button"
        @click="logout"
      >
        <ArrowLeftStartOnRectangleIcon class="h-5 w-5 shrink-0" aria-hidden="true" />
        Đăng xuất
      </button>
    </div>
  </div>
</template>
