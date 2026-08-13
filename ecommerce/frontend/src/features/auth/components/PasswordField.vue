<script setup lang="ts">
import { EyeIcon, EyeSlashIcon } from '@heroicons/vue/24/outline'
import { ref } from 'vue'

defineProps<{
  id: string
  label: string
  modelValue: string
  autocomplete: 'current-password' | 'new-password'
  error?: string
  describedBy?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  blur: []
}>()

const visible = ref(false)
</script>

<template>
  <div>
    <label :for="id" class="block text-sm font-medium text-gray-800">{{ label }}</label>
    <div class="relative mt-2">
      <input
        :id="id"
        :value="modelValue"
        class="w-full rounded-xl border px-4 py-3 pe-12 text-base outline-none transition focus:ring-2"
        :class="
          error
            ? 'border-red-500 focus:border-red-500 focus:ring-red-100'
            : 'border-gray-300 focus:border-indigo-500 focus:ring-indigo-100'
        "
        :type="visible ? 'text' : 'password'"
        :autocomplete="autocomplete"
        :aria-invalid="Boolean(error)"
        :aria-describedby="
          [describedBy, error ? `${id}-error` : ''].filter(Boolean).join(' ') || undefined
        "
        required
        @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
        @blur="emit('blur')"
      />
      <button
        class="absolute inset-y-0 end-0 flex w-12 items-center justify-center rounded-e-xl text-gray-500 transition hover:text-indigo-600 focus-visible:outline-2 focus-visible:outline-offset-[-4px] focus-visible:outline-indigo-600"
        type="button"
        :aria-label="visible ? `Ẩn ${label.toLowerCase()}` : `Hiện ${label.toLowerCase()}`"
        :aria-pressed="visible"
        @click="visible = !visible"
      >
        <EyeSlashIcon v-if="visible" class="size-5" aria-hidden="true" />
        <EyeIcon v-else class="size-5" aria-hidden="true" />
      </button>
    </div>
    <p v-if="error" :id="`${id}-error`" class="mt-1.5 text-sm text-red-600" role="alert">
      {{ error }}
    </p>
    <slot />
  </div>
</template>
