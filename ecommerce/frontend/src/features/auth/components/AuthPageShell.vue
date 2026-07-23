<script setup lang="ts">
defineProps<{
  eyebrow: string
  title: string
  description?: string
}>()
</script>

<template>
  <main class="flex min-h-screen items-center justify-center px-5 py-12">
    <section class="w-full max-w-md rounded-3xl bg-white p-8 shadow-sm ring-1 ring-gray-200">
      <RouterLink class="text-sm font-semibold text-indigo-600 hover:text-indigo-500" to="/">
        Multi-Vendor AI E-commerce
      </RouterLink>
      <p class="mt-8 text-xs font-bold uppercase tracking-[0.2em] text-indigo-600">{{ eyebrow }}</p>
      <h1 class="mt-2 text-3xl font-bold tracking-tight text-gray-950">{{ title }}</h1>
      <p v-if="description" class="mt-3 text-sm leading-6 text-gray-600">{{ description }}</p>
      <div class="mt-8">
        <slot />
      </div>
    </section>
  </main>
</template>
