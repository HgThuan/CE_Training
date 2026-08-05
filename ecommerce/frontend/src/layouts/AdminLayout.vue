<script setup lang="ts">
import { ref } from 'vue'
import { RouterView } from 'vue-router'
import { Bars3Icon } from '@heroicons/vue/24/outline'
import AppSidebar from '@/components/layout/AppSidebar.vue'

const sidebarOpen = ref(false)
</script>

<template>
  <div class="flex h-screen bg-slate-100 overflow-hidden">
    <AppSidebar v-model:is-open="sidebarOpen" />
    
    <div class="flex flex-1 flex-col overflow-hidden w-full">
      <header class="flex h-16 shrink-0 items-center justify-between border-b border-slate-800 bg-slate-950 px-4 text-white sm:px-6">
        <div class="flex items-center gap-4">
          <button 
            type="button" 
            class="lg:hidden p-2 -ml-2 text-slate-300 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 rounded-md" 
            aria-label="Open sidebar"
            :aria-expanded="sidebarOpen"
            @click="sidebarOpen = true"
          >
            <Bars3Icon class="h-6 w-6" aria-hidden="true" />
          </button>
          
          <RouterLink class="flex items-center gap-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 rounded-md" to="/admin">
            <span class="grid h-10 w-10 place-items-center rounded-2xl bg-indigo-500 font-black">M</span>
            <div class="hidden sm:block">
              <p class="text-xs font-bold uppercase tracking-widest text-indigo-300">Mercato</p>
              <p class="text-sm font-black">Admin Console</p>
            </div>
          </RouterLink>
        </div>
      </header>

      <main class="flex-1 overflow-y-auto outline-none" tabindex="-1">
        <RouterView />
      </main>
    </div>
  </div>
</template>
