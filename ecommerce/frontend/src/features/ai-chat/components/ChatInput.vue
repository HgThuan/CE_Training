<script setup lang="ts">
import { SparklesIcon } from '@heroicons/vue/24/outline'
import { PaperAirplaneIcon } from '@heroicons/vue/24/solid'
import { nextTick, ref } from 'vue'

const props = defineProps<{ disabled: boolean }>()
const emit = defineEmits<{ send: [message: string] }>()
const message = ref('')
const textarea = ref<HTMLTextAreaElement | null>(null)

function resizeTextarea(): void {
  if (!textarea.value) return
  textarea.value.style.height = 'auto'
  textarea.value.style.height = `${Math.min(textarea.value.scrollHeight, 112)}px`
}

function submit(): void {
  const normalized = message.value.trim()
  if (!normalized || props.disabled) return
  emit('send', normalized)
  message.value = ''
  void nextTick(resizeTextarea)
}

function handleKeydown(event: KeyboardEvent): void {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    submit()
  }
}
</script>

<template>
  <form class="ai-chat-composer" @submit.prevent="submit">
    <div class="ai-chat-composer__field">
      <label class="sr-only" for="ai-chat-message">Nội dung cần tư vấn</label>
      <textarea
        id="ai-chat-message"
        ref="textarea"
        v-model="message"
        class="ai-chat-composer__textarea"
        rows="1"
        maxlength="1000"
        :disabled="disabled"
        :placeholder="disabled ? 'Trợ lý đang trả lời…' : 'Nhập nhu cầu hoặc câu hỏi…'"
        @input="resizeTextarea"
        @keydown="handleKeydown"
      />
      <button
        class="ai-chat-composer__send"
        type="submit"
        :disabled="disabled || !message.trim()"
        aria-label="Gửi tin nhắn"
      >
        <PaperAirplaneIcon class="size-5" aria-hidden="true" />
        <span>Gửi</span>
      </button>
    </div>
    <div class="ai-chat-composer__meta">
      <p>
        <SparklesIcon aria-hidden="true" />
        AI có thể nhầm. Hãy kiểm tra giá và chính sách trước khi mua.
      </p>
      <span>Enter để gửi</span>
    </div>
  </form>
</template>

<style scoped>
.ai-chat-composer {
  padding: 0.75rem 0.875rem calc(0.75rem + env(safe-area-inset-bottom));
  background: #fffdf8;
  box-shadow: 0 -8px 24px rgb(23 59 53 / 6%);
}

.ai-chat-composer__field {
  display: flex;
  align-items: end;
  gap: 0.5rem;
  border: 1px solid rgb(23 59 53 / 38%);
  border-radius: 0.875rem;
  padding: 0.35rem;
  background: white;
  transition:
    border-color 160ms ease-out,
    box-shadow 160ms ease-out;
}

.ai-chat-composer__field:focus-within {
  border-color: #e85d3f;
  box-shadow: 0 0 0 3px rgb(232 93 63 / 14%);
}

.ai-chat-composer__textarea {
  min-height: 2.75rem;
  max-height: 7rem;
  min-width: 0;
  flex: 1;
  resize: none;
  overflow-y: auto;
  border: 0;
  padding: 0.65rem 0.65rem 0.55rem;
  color: #0b2a25;
  background: transparent;
  font-size: 0.9375rem;
  line-height: 1.4;
}

.ai-chat-composer__textarea::placeholder {
  color: #667974;
}

.ai-chat-composer__textarea:focus {
  outline: 0;
}

.ai-chat-composer__textarea:disabled {
  cursor: not-allowed;
  color: #526762;
}

.ai-chat-composer__send {
  display: inline-flex;
  min-height: 2.75rem;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  border: 0;
  border-radius: 0.7rem;
  padding-inline: 0.85rem;
  color: white;
  background: #e85d3f;
  font-size: 0.8125rem;
  font-weight: 850;
  transition:
    background-color 160ms ease-out,
    transform 160ms ease-out;
}

.ai-chat-composer__send:hover:not(:disabled) {
  background: #c8452d;
  transform: translateY(-1px);
}

.ai-chat-composer__send:focus-visible {
  outline: 3px solid rgb(232 93 63 / 40%);
  outline-offset: 2px;
}

.ai-chat-composer__send:disabled {
  cursor: not-allowed;
  background: #d99c8d;
}

.ai-chat-composer__meta {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 0.75rem;
  margin-top: 0.45rem;
  padding-inline: 0.2rem;
  color: #667974;
  font-size: 0.675rem;
  line-height: 1.4;
}

.ai-chat-composer__meta p {
  display: flex;
  min-width: 0;
  align-items: start;
  gap: 0.3rem;
}

.ai-chat-composer__meta svg {
  width: 0.85rem;
  height: 0.85rem;
  flex: 0 0 auto;
  margin-top: 0.05rem;
}

.ai-chat-composer__meta > span {
  flex: 0 0 auto;
}

@media (max-width: 380px) {
  .ai-chat-composer__send span,
  .ai-chat-composer__meta > span {
    display: none;
  }

  .ai-chat-composer__send {
    width: 2.75rem;
    padding: 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .ai-chat-composer__send {
    transition: none;
  }
}
</style>
