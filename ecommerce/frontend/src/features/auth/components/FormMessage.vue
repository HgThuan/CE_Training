<script setup lang="ts">
defineProps<{
  message: string
  variant?: 'error' | 'success'
}>()
</script>

<template>
  <p
    class="rounded-xl px-4 py-3 text-sm"
    :class="variant === 'success' ? 'bg-emerald-50 text-emerald-800' : 'bg-red-50 text-red-700'"
    role="status"
  >
    {{ message }}
  </p>
</template>
