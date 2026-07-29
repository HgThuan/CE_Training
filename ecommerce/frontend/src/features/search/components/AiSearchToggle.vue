<script setup lang="ts">
import { SparklesIcon } from '@heroicons/vue/24/outline'

withDefaults(
  defineProps<{
    modelValue: boolean
    compact?: boolean
    disabled?: boolean
  }>(),
  {
    compact: false,
    disabled: false,
  },
)

const emit = defineEmits<{
  'update:modelValue': [enabled: boolean]
}>()

function updateValue(event: Event): void {
  emit('update:modelValue', (event.target as HTMLInputElement).checked)
}
</script>

<template>
  <label
    class="inline-flex h-11 shrink-0 items-center gap-1.5 rounded-xl border px-2.5 text-xs font-black transition focus-within:ring-4 focus-within:ring-indigo-100"
    :class="[
      modelValue
        ? 'border-indigo-600 bg-indigo-600 text-white'
        : 'border-slate-300 bg-white text-slate-600 hover:border-indigo-300',
      disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer',
    ]"
  >
    <input
      class="sr-only"
      type="checkbox"
      role="switch"
      aria-label="AI Search"
      :checked="modelValue"
      :disabled="disabled"
      @change="updateValue"
    />
    <SparklesIcon class="h-4 w-4" aria-hidden="true" />
    <span>{{ compact ? 'AI' : 'AI Search' }}</span>
  </label>
</template>
