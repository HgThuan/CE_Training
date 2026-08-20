<script setup lang="ts">
import {
  ArrowsRightLeftIcon,
  CheckBadgeIcon,
  CheckIcon,
  ClipboardDocumentIcon,
  HandThumbDownIcon,
  HandThumbUpIcon,
  LightBulbIcon,
  ShoppingBagIcon,
  TagIcon,
  TruckIcon,
  UserGroupIcon,
} from '@heroicons/vue/24/outline'
import { SparklesIcon } from '@heroicons/vue/24/solid'
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'

import ProductCompareTable from '@/features/product/components/ProductCompareTable.vue'
import { formatVnd } from '@/shared/lib/formatters'

import type {
  ChatMessage,
  HandoffAttachment,
  OrderSupportAttachment,
  ProductCardAttachment,
  PromotionAttachment,
  QuickActionsAttachment,
} from '../types'
import ChatProductCard from './ChatProductCard.vue'
import ChatRichText from './ChatRichText.vue'

const props = defineProps<{ messages: ChatMessage[]; isStreaming: boolean }>()
const emit = defineEmits<{
  followUp: [message: string]
  feedback: [messageId: string, rating: number]
}>()
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
  if (
    message.attachments.some(
      (item) => item.type === 'quick_actions' || item.type === 'handoff_card',
    )
  )
    return []
  const productCount = message.attachments.filter((item) => item.type === 'product_card').length
  if (productCount >= 2) return ['So sánh các sản phẩm này', 'Tìm lựa chọn khác']
  if (productCount === 1) return ['Tìm sản phẩm tương tự', 'Hỏi về phí giao hàng']
  return ['Tìm sản phẩm phù hợp', 'Hỏi chính sách đổi trả']
}

function productCards(
  message: ChatMessage,
  kind: 'exact' | 'alternative' | 'personalized',
): ProductCardAttachment[] {
  return message.attachments.filter(
    (item): item is ProductCardAttachment =>
      item.type === 'product_card' &&
      (item.match?.kind === kind || (kind === 'alternative' && !item.match)),
  )
}

function orderCards(message: ChatMessage): OrderSupportAttachment[] {
  return message.attachments.filter(
    (item): item is OrderSupportAttachment => item.type === 'order_card',
  )
}

function promotionCards(message: ChatMessage): PromotionAttachment[] {
  return message.attachments.filter(
    (item): item is PromotionAttachment => item.type === 'promotion_card',
  )
}

function quickActionGroups(message: ChatMessage): QuickActionsAttachment[] {
  return message.attachments.filter(
    (item): item is QuickActionsAttachment => item.type === 'quick_actions',
  )
}

function handoffCards(message: ChatMessage): HandoffAttachment[] {
  return message.attachments.filter(
    (item): item is HandoffAttachment => item.type === 'handoff_card',
  )
}

function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat('vi-VN', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(value))
}

function promotionValue(promotion: PromotionAttachment['promotion']): string {
  if (promotion.discount_type === 'freeship') return 'Miễn phí vận chuyển'
  if (promotion.discount_type === 'percent') return `Giảm ${Number(promotion.discount_value)}%`
  return `Giảm ${formatVnd(promotion.discount_value)}`
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
            v-if="productCards(message, 'personalized').length"
            class="ai-chat-answer__section"
            aria-label="Gợi ý dành cho bạn"
          >
            <h3 class="ai-chat-answer__section-title">
              <ShoppingBagIcon class="size-4" aria-hidden="true" />
              Dành cho bạn
            </h3>
            <ul class="space-y-2.5">
              <li
                v-for="attachment in productCards(message, 'personalized')"
                :key="attachment.product_id"
              >
                <ChatProductCard :product="attachment.product" />
              </li>
            </ul>
          </div>

          <section
            v-for="attachment in orderCards(message)"
            :key="attachment.order.id"
            class="ai-chat-answer__section rounded-2xl border border-[#cad9d3] bg-white p-3.5 shadow-sm"
            aria-label="Thông tin đơn hàng"
          >
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <p class="text-[0.68rem] font-bold tracking-wide text-[#667974] uppercase">
                  Đơn hàng
                </p>
                <h3 class="mt-0.5 truncate text-sm font-black text-[#0b2a25]">
                  {{ attachment.order.order_code }}
                </h3>
              </div>
              <span
                class="shrink-0 rounded-full bg-[#e8eee9] px-2.5 py-1 text-[0.68rem] font-black text-[#173b35]"
              >
                {{ attachment.order.payment_status_label }}
              </span>
            </div>
            <div class="mt-3 space-y-2.5">
              <article
                v-for="shop in attachment.order.shop_orders"
                :key="shop.id"
                class="rounded-xl bg-[#f7f3ea] p-3"
              >
                <div class="flex items-center justify-between gap-2">
                  <strong class="truncate text-xs text-[#173b35]">{{ shop.shop_name }}</strong>
                  <span class="shrink-0 text-[0.68rem] font-bold text-[#e85d3f]">
                    {{ shop.fulfillment_status_label }}
                  </span>
                </div>
                <p class="mt-1.5 flex items-center gap-1.5 text-[0.7rem] text-[#667974]">
                  <TruckIcon class="size-3.5" aria-hidden="true" />
                  {{ shop.shipping_method }} · cập nhật {{ formatDateTime(shop.last_status_at) }}
                </p>
                <p class="mt-1.5 truncate text-[0.7rem] text-[#526762]">
                  {{ shop.items.map((item) => `${item.name} × ${item.quantity}`).join(', ') }}
                </p>
                <p
                  v-if="shop.return_requests.length"
                  class="mt-2 rounded-lg bg-amber-50 px-2.5 py-1.5 text-[0.7rem] font-bold text-amber-900"
                >
                  Đổi/trả: {{ shop.return_requests[0].status_label }}
                </p>
                <p
                  v-else-if="shop.return_eligible"
                  class="mt-2 rounded-lg bg-emerald-50 px-2.5 py-1.5 text-[0.7rem] font-bold text-emerald-900"
                >
                  Có thể mở yêu cầu trả hàng đến
                  {{ formatDateTime(shop.return_deadline!) }}
                </p>
              </article>
            </div>
            <div class="mt-3 flex items-center justify-between text-xs">
              <span class="text-[#667974]">{{ attachment.order.payment_method_label }}</span>
              <strong class="text-[#0b2a25]">{{ formatVnd(attachment.order.grand_total) }}</strong>
            </div>
          </section>

          <section
            v-for="attachment in promotionCards(message)"
            :key="attachment.promotion.id"
            class="ai-chat-answer__section rounded-2xl border border-dashed border-[#e85d3f] bg-[#fff8ed] p-3.5"
            aria-label="Mã giảm giá"
          >
            <div class="flex items-start gap-3">
              <span
                class="grid size-9 shrink-0 place-items-center rounded-xl bg-[#e85d3f] text-white"
              >
                <TagIcon class="size-4.5" aria-hidden="true" />
              </span>
              <div class="min-w-0 flex-1">
                <div class="flex items-start justify-between gap-2">
                  <div>
                    <h3 class="text-sm font-black text-[#0b2a25]">
                      {{ attachment.promotion.code }}
                    </h3>
                    <p class="text-[0.7rem] font-bold text-[#667974]">
                      {{ attachment.promotion.shop_name }}
                    </p>
                  </div>
                  <span
                    v-if="attachment.promotion.saved"
                    class="rounded-full bg-emerald-100 px-2 py-1 text-[0.65rem] font-black text-emerald-800"
                  >
                    Đã lưu
                  </span>
                </div>
                <p class="mt-2 text-xs font-black text-[#e85d3f]">
                  {{ promotionValue(attachment.promotion) }}
                </p>
                <p class="mt-1 text-[0.7rem] leading-5 text-[#526762]">
                  Đơn tối thiểu {{ formatVnd(attachment.promotion.min_order_amount) }} · hết hạn
                  {{ formatDateTime(attachment.promotion.valid_until) }}
                </p>
              </div>
            </div>
          </section>

          <section
            v-for="attachment in handoffCards(message)"
            :key="attachment.handoff.id"
            class="ai-chat-answer__section rounded-2xl border border-blue-200 bg-blue-50 p-3.5"
            aria-label="Chuyển tiếp nhân viên"
          >
            <div class="flex items-center gap-3">
              <span
                class="grid size-9 shrink-0 place-items-center rounded-xl bg-blue-700 text-white"
              >
                <UserGroupIcon class="size-4.5" aria-hidden="true" />
              </span>
              <div>
                <h3 class="text-sm font-black text-blue-950">Đã chuyển sang CSKH</h3>
                <p class="mt-0.5 text-[0.7rem] text-blue-800">
                  Mã {{ attachment.handoff.id }} · {{ attachment.handoff.status_label }}
                </p>
              </div>
            </div>
          </section>

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

          <div
            v-for="(group, groupIndex) in quickActionGroups(message)"
            :key="`actions-${groupIndex}`"
            class="ai-chat-answer__follow-ups"
            aria-label="Thao tác nhanh"
          >
            <template v-for="action in group.actions" :key="`${action.kind}-${action.value}`">
              <RouterLink v-if="action.kind === 'link'" :to="action.value">
                {{ action.label }}
              </RouterLink>
              <button v-else type="button" @click="emit('followUp', action.value)">
                {{ action.label }}
              </button>
            </template>
          </div>

          <div
            v-if="message.content && !(isStreaming && message === messages.at(-1))"
            class="ai-chat-answer__feedback"
            aria-label="Đánh giá câu trả lời"
          >
            <span>Câu trả lời hữu ích?</span>
            <button
              type="button"
              :class="{ 'is-selected': message.feedback?.rating === 5 }"
              :aria-pressed="message.feedback?.rating === 5"
              aria-label="Câu trả lời hữu ích"
              @click="emit('feedback', message.id, 5)"
            >
              <HandThumbUpIcon aria-hidden="true" />
            </button>
            <button
              type="button"
              :class="{ 'is-selected': message.feedback?.rating === 1 }"
              :aria-pressed="message.feedback?.rating === 1"
              aria-label="Câu trả lời chưa hữu ích"
              @click="emit('feedback', message.id, 1)"
            >
              <HandThumbDownIcon aria-hidden="true" />
            </button>
          </div>

          <footer
            v-if="
              isLatestAssistant(message, messageIndex) && !isStreaming && followUps(message).length
            "
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
.ai-chat-answer__follow-ups,
.ai-chat-answer__feedback {
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

.ai-chat-answer__follow-ups button,
.ai-chat-answer__follow-ups a {
  display: inline-flex;
  min-height: 2.75rem;
  align-items: center;
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

.ai-chat-answer__follow-ups button:hover,
.ai-chat-answer__follow-ups a:hover {
  border-color: #173b35;
  color: white;
  background: #173b35;
}

.ai-chat-answer__follow-ups button:focus-visible,
.ai-chat-answer__follow-ups a:focus-visible {
  outline: 3px solid rgb(232 93 63 / 35%);
  outline-offset: 2px;
}

.ai-chat-answer__feedback {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  margin-top: 0.8rem;
  color: #667974;
  font-size: 0.7rem;
  font-weight: 700;
}

.ai-chat-answer__feedback button {
  display: grid;
  width: 2.5rem;
  height: 2.5rem;
  place-items: center;
  border-radius: 0.65rem;
  color: #526762;
}

.ai-chat-answer__feedback button:hover,
.ai-chat-answer__feedback button.is-selected {
  color: #173b35;
  background: #e8eee9;
}

.ai-chat-answer__feedback svg {
  width: 1rem;
  height: 1rem;
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
  .ai-chat-answer__follow-ups,
  .ai-chat-answer__feedback {
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
