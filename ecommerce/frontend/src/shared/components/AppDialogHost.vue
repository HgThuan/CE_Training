<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'

import { useAppDialogHost } from '@/shared/composables/useAppDialog'

const { state, confirm, submitPrompt, cancel } = useAppDialogHost()
const inputValue = ref('')
const inputElement = ref<HTMLInputElement | null>(null)
const confirmButton = ref<HTMLButtonElement | null>(null)

watch(
  () => state.open,
  async (open) => {
    if (!open) return
    inputValue.value = state.initialValue
    await nextTick()
    ;(state.mode === 'prompt' ? inputElement.value : confirmButton.value)?.focus()
  },
)

function accept(): void {
  if (state.mode === 'prompt') {
    if (state.required && !inputValue.value.trim()) return
    submitPrompt(inputValue.value)
    return
  }
  confirm()
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="state.open"
      class="fixed inset-0 z-[100] grid place-items-center bg-slate-950/55 p-4 backdrop-blur-sm"
      @keydown.esc="cancel"
    >
      <form
        class="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl ring-1 ring-slate-200"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="'app-dialog-title'"
        @submit.prevent="accept"
      >
        <h2 id="app-dialog-title" class="text-xl font-black text-slate-950">{{ state.title }}</h2>
        <p v-if="state.message" class="mt-2 whitespace-pre-line text-sm leading-6 text-slate-600">
          {{ state.message }}
        </p>

        <label v-if="state.mode === 'prompt'" class="mt-5 block">
          <span class="text-sm font-bold text-slate-800">{{ state.inputLabel }}</span>
          <input
            ref="inputElement"
            v-model="inputValue"
            class="mt-2 w-full rounded-xl border border-slate-300 px-3 py-2.5 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
            :placeholder="state.placeholder"
            :required="state.required"
          />
        </label>

        <div class="mt-6 flex justify-end gap-3">
          <button
            class="rounded-xl border border-slate-300 px-4 py-2.5 text-sm font-bold text-slate-700 hover:bg-slate-50"
            type="button"
            @click="cancel"
          >
            {{ state.cancelLabel }}
          </button>
          <button
            ref="confirmButton"
            class="rounded-xl px-4 py-2.5 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-50"
            :class="
              state.destructive
                ? 'bg-rose-600 hover:bg-rose-700'
                : 'bg-indigo-600 hover:bg-indigo-700'
            "
            type="submit"
            :disabled="state.mode === 'prompt' && state.required && !inputValue.trim()"
          >
            {{ state.confirmLabel }}
          </button>
        </div>
      </form>
    </div>
  </Teleport>
</template>
