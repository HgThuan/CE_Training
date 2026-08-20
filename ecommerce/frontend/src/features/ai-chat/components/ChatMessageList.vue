<script setup lang="ts">
import {
  ArrowsRightLeftIcon,
  CheckBadgeIcon,
  CheckIcon,
  ClipboardDocumentIcon,
  LightBulbIcon,
} from '@heroicons/vue/24/outline'
import { SparklesIcon } from '@heroicons/vue/24/solid'
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'

import ProductCompareTable from '@/features/product/components/ProductCompareTable.vue'
import { formatVnd } from '@/shared/lib/formatters'

import type { ChatMessage, ProductCardAttachment } from '../types'
import ChatProductCard from './ChatProductCard.vue'
import ChatRichText from './ChatRichText.vue'

const props = defineProps<{ messages: ChatMessage[]; isStreaming: boolean }>()
const emit = defineEmits<{ followUp: [message: string] }>()
const scroller = ref<HTMLElement | null>(null)
const shouldFollowLatest = ref(true)
const copiedMessageId = ref<string | null>(null)
let copiedTimer: ReturnType<typeof setTimeout> | null = null

onBeforeUnmount(() => {
  if (copiedTimer) clearTimeout(copiedTimer)
})

function isLatestAssistant(message: ChatMessage, index: number): boolean {
  return message.role === 'assistant' && index === props.messages.length - 1
}

function followUps(message: ChatMessage): string[] {
  const productCount = message.attachments.filter((item) => item.type === 'product_card').length
  if (productCount >= 2) return ['So sánh các sản phẩm này', 'Tìm lựa chọn khác']
  if (productCount === 1) return ['Tìm sản phẩm tương tự', 'Hỏi về phí giao hàng']
  return ['Tìm sản phẩm phù hợp', 'Hỏi chính sách đổi trả']
}

function productCards(
  message: ChatMessage,
  kind: 'exact' | 'alternative',
): ProductCardAttachment[] {
  return message.attachments.filter(
    (item): item is ProductCardAttachment =>
      item.type === 'product_card' &&
      (kind === 'exact' ? item.match?.kind === 'exact' : item.match?.kind !== 'exact'),
  )
}

function alternativeCaveat(message: ChatMessage): string {
  const missingTerms = productCards(message, 'alternative').flatMap(
    (attachment) => attachment.match?.missing_terms ?? [],
  )
  const maxBudget = missingTerms.find((term) => term.startsWith('budget_max:'))?.split(':', 2)[1]
  const minBudget = missingTerms.find((term) => term.startsWith('budget_min:'))?.split(':', 2)[1]
  if (maxBudget) {
    return `Các lựa chọn này vượt ngân sách tối đa ${formatVnd(maxBudget)} bạn đã nêu.`
  }
  if (minBudget) {
    return `Các lựa chọn này thấp hơn khoảng giá tối thiểu ${formatVnd(minBudget)} bạn đã nêu.`
  }
  return 'Các sản phẩm này chỉ khớp một phần. Mercato chưa có đủ dữ liệu để xác nhận toàn bộ tiêu chí bạn yêu cầu.'
}

async function copyMessage(message: ChatMessage): Promise<void> {
  if (!navigator.clipboard?.writeText) return
  await navigator.clipboard.writeText(message.content)
  copiedMessageId.value = message.id
  if (copiedTimer) clearTimeout(copiedTimer)
  copiedTimer = setTimeout(() => {
    copiedMessageId.value = null
  }, 1800)
}

function updateScrollPosition(): void {
  if (!scroller.value) return
  const distanceFromBottom =
    scroller.value.scrollHeight - scroller.value.scrollTop - scroller.value.clientHeight
  shouldFollowLatest.value = distanceFromBottom < 80
}

watch(
  () => [props.messages.length, props.messages.at(-1)?.content, props.isStreaming],
  async () => {
    if (!shouldFollowLatest.value) return
    await nextTick()
    const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    scroller.value?.scrollTo?.({
      top: scroller.value.scrollHeight,
      behavior: props.isStreaming || reducedMotion ? 'auto' : 'smooth',
    })
  },
)
</script>

<template>
  <div
    ref="scroller"
    class="min-h-0 flex-1 overflow-y-auto bg-[#f7f3ea] px-3 py-4"
    @scroll.passive="updateScrollPosition"
  >
    <ol class="space-y-4" aria-live="polite" aria-label="Nội dung hội thoại">
      <li
        v-for="(message, messageIndex) in messages"
        :key="message.id"
        class="flex"
        :class="message.role === 'user' ? 'justify-end' : 'justify-start'"
      >
        <div v-if="message.role === 'user'" class="max-w-[84%] min-w-0">
          <div
            class="whitespace-pre-wrap rounded-2xl rounded-br-md bg-[#173b35] px-4 py-2.5 text-[0.9375rem] leading-6 text-white shadow-[0_8px_20px_rgba(23,59,53,0.12)]"
          >
            {{ message.content }}
          </div>
        </div>

        <article
          v-else
          class="ai-chat-answer"
          :aria-busy="isStreaming && message === messages.at(-1) ? 'true' : undefined"
        >
          <header class="ai-chat-answer__header">
            <span class="ai-chat-answer__avatar">
              <SparklesIcon aria-hidden="true" />
            </span>
            <div class="min-w-0 flex-1">
              <h2>Mercato AI</h2>
              <p>
                {{ isStreaming && message === messages.at(-1) ? 'Đang trả lời' : 'Tư vấn mua sắm' }}
              </p>
            </div>
            <button
              v-if="message.content && !isStreaming"
              class="ai-chat-answer__copy"
              type="button"
              :aria-label="
                copiedMessageId === message.id ? 'Đã sao chép câu trả lời' : 'Sao chép câu trả lời'
              "
              @click="copyMessage(message)"
            >
              <CheckIcon v-if="copiedMessageId === message.id" aria-hidden="true" />
              <ClipboardDocumentIcon v-else aria-hidden="true" />
              <span>{{ copiedMessageId === message.id ? 'Đã chép' : 'Sao chép' }}</span>
            </button>
          </header>

          <div class="ai-chat-answer__body">
            <ChatRichText v-if="message.content" :content="message.content" />
            <span
              v-else-if="isStreaming && message === messages.at(-1)"
              class="inline-flex items-center gap-1.5 text-[#526762]"
            >
              <span class="ai-chat-typing-dot" />
              <span class="ai-chat-typing-dot" />
              <span class="ai-chat-typing-dot" />
              <span class="sr-only">Trợ lý đang trả lời</span>
            </span>
          </div>

          <div
            v-if="productCards(message, 'exact').length"
            class="ai-chat-answer__section"
            aria-label="Sản phẩm khớp với nhu cầu"
          >
            <h3 class="ai-chat-answer__section-title">
              <CheckBadgeIcon class="size-4" aria-hidden="true" />
              Khớp với nhu cầu
            </h3>
            <ul class="space-y-2.5">
              <li v-for="attachment in productCards(message, 'exact')" :key="attachment.product_id">
                <ChatProductCard :product="attachment.product" />
              </li>
            </ul>
          </div>

          <div
            v-if="productCards(message, 'alternative').length"
            class="ai-chat-answer__section ai-chat-answer__section--alternatives"
            aria-label="Sản phẩm gần với nhu cầu"
          >
            <h3 class="ai-chat-answer__section-title">
              <LightBulbIcon class="size-4" aria-hidden="true" />
              Gợi ý gần nhu cầu
            </h3>
            <p class="ai-chat-answer__section-help">
              {{ alternativeCaveat(message) }}
            </p>
            <ul class="space-y-2.5">
              <li
                v-for="attachment in productCards(message, 'alternative')"
                :key="attachment.product_id"
              >
                <ChatProductCard :product="attachment.product" />
              </li>
            </ul>
          </div>

          <div
            v-for="attachment in message.attachments.filter(
              (item) => item.type === 'compare_table',
            )"
            :key="attachment.product_ids.join('-')"
            class="ai-chat-answer__section ai-chat-compare overflow-x-auto"
          >
            <h3 class="ai-chat-answer__section-title">
              <ArrowsRightLeftIcon class="size-4" aria-hidden="true" />
              So sánh nhanh
            </h3>
            <ProductCompareTable :comparison="attachment.comparison" />
          </div>

          <footer
            v-if="isLatestAssistant(message, messageIndex) && !isStreaming"
            class="ai-chat-answer__follow-ups"
            aria-label="Gợi ý hỏi tiếp"
          >
            <button
              v-for="suggestion in followUps(message)"
              :key="suggestion"
              type="button"
              @click="emit('followUp', suggestion)"
            >
              {{ suggestion }}
            </button>
          </footer>
        </article>
      </li>
    </ol>
  </div>
</template>

<style scoped>
.ai-chat-answer {
  width: 100%;
  min-width: 0;
  padding: 0.2rem 0.25rem 1.15rem;
  border-bottom: 1px solid rgb(23 59 53 / 12%);
}

.ai-chat-answer__header {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.ai-chat-answer__avatar {
  display: grid;
  width: 2.25rem;
  height: 2.25rem;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 0.7rem;
  color: #0b2a25;
  background: #f2c14e;
}

.ai-chat-answer__avatar svg {
  width: 1.1rem;
  height: 1.1rem;
}

.ai-chat-answer__header h2 {
  color: #0b2a25;
  font-size: 0.875rem;
  font-weight: 850;
  line-height: 1.2;
}

.ai-chat-answer__header p {
  margin-top: 0.12rem;
  color: #667974;
  font-size: 0.7rem;
  line-height: 1.2;
}

.ai-chat-answer__copy {
  display: inline-flex;
  min-height: 2.75rem;
  flex: 0 0 auto;
  align-items: center;
  gap: 0.35rem;
  border: 0;
  border-radius: 0.7rem;
  padding-inline: 0.65rem;
  color: #526762;
  background: transparent;
  font-size: 0.7rem;
  font-weight: 750;
}

.ai-chat-answer__copy:hover {
  color: #173b35;
  background: #e8eee9;
}

.ai-chat-answer__copy:focus-visible {
  outline: 3px solid rgb(232 93 63 / 35%);
  outline-offset: 1px;
}

.ai-chat-answer__copy svg {
  width: 1rem;
  height: 1rem;
}

.ai-chat-answer__body,
.ai-chat-answer__section,
.ai-chat-answer__follow-ups {
  margin-left: 2.9rem;
}

.ai-chat-answer__body {
  margin-top: 0.8rem;
}

.ai-chat-answer__section {
  margin-top: 1rem;
}

.ai-chat-answer__section-title {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  margin-bottom: 0.6rem;
  color: #173b35;
  font-size: 0.8rem;
  font-weight: 850;
}

.ai-chat-answer__section-title svg {
  width: 1rem;
  height: 1rem;
}

.ai-chat-answer__section-help {
  margin: -0.15rem 0 0.7rem;
  color: #526762;
  font-size: 0.75rem;
  line-height: 1.45;
}

.ai-chat-answer__section--alternatives {
  border-radius: 0.875rem;
  background: rgb(242 193 78 / 12%);
  padding: 0.75rem;
}

.ai-chat-answer__follow-ups {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 1rem;
}

.ai-chat-answer__follow-ups button {
  min-height: 2.75rem;
  border: 1px solid rgb(23 59 53 / 22%);
  border-radius: 0.7rem;
  padding: 0.55rem 0.7rem;
  color: #173b35;
  background: #fffdf8;
  font-size: 0.75rem;
  font-weight: 800;
  transition:
    color 160ms ease-out,
    border-color 160ms ease-out,
    background-color 160ms ease-out;
}

.ai-chat-answer__follow-ups button:hover {
  border-color: #173b35;
  color: white;
  background: #173b35;
}

.ai-chat-answer__follow-ups button:focus-visible {
  outline: 3px solid rgb(232 93 63 / 35%);
  outline-offset: 2px;
}

.ai-chat-typing-dot {
  width: 0.38rem;
  height: 0.38rem;
  border-radius: 999px;
  background: #526762;
  animation: ai-chat-pulse 1.1s ease-in-out infinite;
}

@media (max-width: 420px) {
  .ai-chat-answer__body,
  .ai-chat-answer__section,
  .ai-chat-answer__follow-ups {
    margin-left: 0;
  }

  .ai-chat-answer__body {
    margin-top: 0.9rem;
  }

  .ai-chat-answer__copy span {
    display: none;
  }

  .ai-chat-answer__copy {
    width: 2.75rem;
    justify-content: center;
    padding: 0;
  }
}

.ai-chat-typing-dot:nth-child(2) {
  animation-delay: 120ms;
}

.ai-chat-typing-dot:nth-child(3) {
  animation-delay: 240ms;
}

.ai-chat-compare :deep(section) {
  margin-top: 0;
  border-radius: 1rem;
}

@keyframes ai-chat-pulse {
  0%,
  70%,
  100% {
    opacity: 0.35;
    transform: translateY(0);
  }
  35% {
    opacity: 1;
    transform: translateY(-2px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .ai-chat-typing-dot {
    animation: none;
  }
}
</style>
