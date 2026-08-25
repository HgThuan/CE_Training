<script setup lang="ts">
import {
  ArrowPathIcon,
  ChevronRightIcon,
  ChatBubbleLeftRightIcon,
  DocumentTextIcon,
  MagnifyingGlassIcon,
  MinusIcon,
  ScaleIcon,
  SparklesIcon,
  TagIcon,
  TruckIcon,
  UserGroupIcon,
} from '@heroicons/vue/24/outline'
import { storeToRefs } from 'pinia'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { useAuthStore } from '@/stores/auth'
import { useCompareStore } from '@/features/product/compare-store'

import { useChatStore } from '../store'
import ChatInput from './ChatInput.vue'
import ChatMessageList from './ChatMessageList.vue'

const authStore = useAuthStore()
const chatStore = useChatStore()
const compareStore = useCompareStore()
const {
  conversationId,
  conversations,
  messages,
  isStreaming,
  isLoadingHistory,
  errorMessage,
  historyError,
  activeStage,
  lastFailedMessage,
  canUseAssistant,
} = storeToRefs(chatStore)
const { selectedProducts } = storeToRefs(compareStore)
const isOpen = ref(false)
const panel = ref<HTMLElement | null>(null)
const launcher = ref<HTMLButtonElement | null>(null)
const isMobile = ref(false)
let mobileMediaQuery: MediaQueryList | null = null

const stageLabel = computed(() => {
  const labels = {
    understanding: 'Đang hiểu nhu cầu',
    planning: 'Đang lập kế hoạch',
    retrieving: 'Đang kiểm tra dữ liệu Mercato',
    composing: 'Đang soạn câu trả lời',
  }
  return activeStage.value ? labels[activeStage.value] : 'Sẵn sàng tư vấn'
})

const starters = [
  {
    title: 'Tìm laptop học tập',
    description: 'Ngân sách dưới 20 triệu',
    prompt: 'Tìm laptop học tập dưới 20 triệu',
    icon: MagnifyingGlassIcon,
  },
  {
    title: 'Theo dõi đơn hàng',
    description: 'Trạng thái giao và thanh toán mới nhất',
    prompt: 'Kiểm tra đơn hàng gần nhất của tôi',
    icon: TruckIcon,
  },
  {
    title: 'Tìm mã giảm giá',
    description: 'Ưu đãi đang còn hiệu lực',
    prompt: 'Có mã giảm giá nào đang dùng được?',
    icon: TagIcon,
  },
  {
    title: 'So sánh lựa chọn',
    description: 'Đối chiếu điểm khác biệt quan trọng',
    prompt: 'Giúp tôi tìm hai sản phẩm phù hợp để so sánh',
    icon: ScaleIcon,
  },
  {
    title: 'Gặp nhân viên hỗ trợ',
    description: 'Chuyển tiếp cả ngữ cảnh hội thoại',
    prompt: 'Tôi muốn gặp nhân viên hỗ trợ',
    icon: UserGroupIcon,
  },
  {
    title: 'Hỏi chính sách',
    description: 'Giao hàng, thanh toán và đổi trả',
    prompt: 'Chính sách đổi trả của Mercato thế nào?',
    icon: DocumentTextIcon,
  },
]

function syncMobileMode(event: MediaQueryList | MediaQueryListEvent): void {
  isMobile.value = event.matches
}

onMounted(() => {
  void chatStore.initialize()
  if (typeof window.matchMedia === 'function') {
    mobileMediaQuery = window.matchMedia('(max-width: 639px)')
    syncMobileMode(mobileMediaQuery)
    mobileMediaQuery.addEventListener('change', syncMobileMode)
  }
})
onBeforeUnmount(() => mobileMediaQuery?.removeEventListener('change', syncMobileMode))
watch(
  () => authStore.user?.id ?? null,
  () => void chatStore.initialize(),
)
watch(
  () => selectedProducts.value.length,
  async (count) => {
    if (!count) return
    const wasOpen = isOpen.value
    isOpen.value = false
    if (wasOpen) {
      await nextTick()
      document.getElementById('product-compare-bar')?.focus()
    }
  },
)

function send(message: string): void {
  void chatStore.sendMessage(message)
}

function submitFeedback(messageId: string, rating: number): void {
  void chatStore.submitFeedback(messageId, rating)
}

function selectConversation(event: Event): void {
  const id = (event.target as HTMLSelectElement).value
  if (id) void chatStore.selectConversation(id)
}

async function openChat(): Promise<void> {
  isOpen.value = true
  await nextTick()
  panel.value?.focus()
}

async function closeChat(): Promise<void> {
  isOpen.value = false
  await nextTick()
  launcher.value?.focus()
}

function handlePanelKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    event.preventDefault()
    void closeChat()
    return
  }
  if (!isMobile.value || event.key !== 'Tab' || !panel.value) return
  const focusable = Array.from(
    panel.value.querySelectorAll<HTMLElement>(
      'button:not([disabled]), textarea:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])',
    ),
  )
  if (!focusable.length) return
  const first = focusable[0]
  const last = focusable.at(-1)!
  if (
    event.shiftKey &&
    (document.activeElement === first || document.activeElement === panel.value)
  ) {
    event.preventDefault()
    last.focus()
  } else if (
    !event.shiftKey &&
    (document.activeElement === last || document.activeElement === panel.value)
  ) {
    event.preventDefault()
    first.focus()
  }
}
</script>

<template>
  <div class="ai-chat-layer">
    <button
      v-if="isOpen && isMobile"
      class="ai-chat-scrim"
      type="button"
      aria-label="Đóng trợ lý mua sắm"
      @click="closeChat"
    />
    <Transition name="ai-chat-panel">
      <aside
        v-if="isOpen && !selectedProducts.length"
        id="ai-shopping-assistant"
        ref="panel"
        class="ai-chat-panel"
        aria-label="Trợ lý mua sắm AI"
        :aria-modal="isMobile ? 'true' : undefined"
        :role="isMobile ? 'dialog' : undefined"
        tabindex="-1"
        @keydown="handlePanelKeydown"
      >
        <header class="ai-chat-header">
          <span class="ai-chat-header__mark">
            <SparklesIcon aria-hidden="true" />
          </span>
          <div class="min-w-0 flex-1">
            <h2 class="truncate text-[1.05rem] font-black tracking-[-0.015em]">Trợ lý mua sắm</h2>
            <p class="ai-chat-presence" role="status">
              <span :class="{ 'is-busy': isStreaming }" aria-hidden="true" />
              {{ isStreaming ? stageLabel : 'Sẵn sàng tư vấn' }}
            </p>
          </div>
          <button
            class="grid size-11 place-items-center rounded-xl text-white transition hover:bg-white/10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#f2c14e]"
            type="button"
            title="Bắt đầu cuộc trò chuyện mới"
            aria-label="Bắt đầu cuộc trò chuyện mới"
            @click="chatStore.newConversation"
          >
            <ArrowPathIcon class="size-5" aria-hidden="true" />
          </button>
          <button
            class="grid size-11 place-items-center rounded-xl text-white transition hover:bg-white/10 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#f2c14e]"
            type="button"
            aria-label="Thu gọn trợ lý"
            @click="closeChat"
          >
            <MinusIcon class="size-5" aria-hidden="true" />
          </button>
        </header>

        <div
          v-if="canUseAssistant && conversations.length"
          class="ai-chat-history"
          aria-label="Lịch sử hội thoại"
        >
          <label for="ai-chat-conversation">Cuộc trò chuyện</label>
          <select
            id="ai-chat-conversation"
            :value="conversationId ?? ''"
            :disabled="isStreaming || isLoadingHistory"
            @change="selectConversation"
          >
            <option value="">Cuộc trò chuyện mới</option>
            <option
              v-for="conversation in conversations"
              :key="conversation.id"
              :value="conversation.id"
            >
              {{ conversation.title || 'Cuộc trò chuyện chưa đặt tên' }}
            </option>
          </select>
        </div>

        <div
          v-if="isLoadingHistory"
          class="grid min-h-0 flex-1 place-items-center bg-[#f7f3ea] px-6 text-center text-sm text-[#526762]"
          role="status"
        >
          Đang mở lại cuộc trò chuyện…
        </div>
        <div
          v-else-if="!messages.length"
          class="min-h-0 flex-1 overflow-y-auto bg-[#f7f3ea] px-5 py-7"
        >
          <div class="mx-auto max-w-md">
            <span
              class="grid size-14 place-items-center rounded-2xl bg-[#173b35] text-white shadow-[0_10px_28px_rgba(23,59,53,0.16)]"
            >
              <SparklesIcon class="size-7" aria-hidden="true" />
            </span>
            <h3 class="mt-5 text-2xl font-black tracking-[-0.025em] text-[#0b2a25]">
              Hôm nay bạn muốn tìm gì?
            </h3>
            <p class="mt-2 max-w-[34rem] text-[0.9375rem] leading-6 text-[#526762]">
              Chia sẻ nhu cầu theo cách tự nhiên. Mình sẽ hỏi thêm khi cần và chỉ đề xuất sản phẩm
              đang có trên Mercato.
            </p>
            <div class="mt-6 space-y-2.5" aria-label="Câu hỏi gợi ý">
              <button
                v-for="starter in starters"
                :key="starter.prompt"
                class="ai-chat-starter"
                type="button"
                @click="send(starter.prompt)"
              >
                <span class="ai-chat-starter__icon">
                  <component :is="starter.icon" class="size-5" aria-hidden="true" />
                </span>
                <span class="min-w-0 flex-1">
                  <strong>{{ starter.title }}</strong>
                  <small>{{ starter.description }}</small>
                </span>
                <ChevronRightIcon class="size-4.5 shrink-0 text-[#71827e]" aria-hidden="true" />
              </button>
            </div>
          </div>
        </div>
        <ChatMessageList
          v-else
          :messages="messages"
          :is-streaming="isStreaming"
          @follow-up="send"
          @feedback="submitFeedback"
        />

        <p
          v-if="historyError"
          class="flex items-center justify-between gap-3 border-t border-amber-200 bg-amber-50 px-4 py-2 text-xs font-semibold text-amber-900"
          role="status"
        >
          <span>{{ historyError }}</span>
          <button
            class="shrink-0 rounded-lg border border-amber-800 px-2.5 py-1.5 font-black focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-800"
            type="button"
            @click="chatStore.loadConversations"
          >
            Thử lại
          </button>
        </p>
        <div
          v-if="errorMessage"
          class="flex items-center justify-between gap-3 border-t border-red-200 bg-red-50 px-4 py-2 text-xs font-semibold text-red-800"
          role="status"
        >
          <span>{{ errorMessage }}</span>
          <button
            v-if="lastFailedMessage"
            class="shrink-0 rounded-lg border border-red-800 px-2.5 py-1.5 font-black"
            type="button"
            @click="chatStore.retryLastMessage"
          >
            Gửi lại
          </button>
        </div>
        <ChatInput
          v-if="canUseAssistant"
          :disabled="isStreaming || isLoadingHistory"
          @send="send"
        />
      </aside>
    </Transition>

    <button
      v-if="!isOpen && !selectedProducts.length"
      ref="launcher"
      class="ai-chat-launcher"
      type="button"
      aria-controls="ai-shopping-assistant"
      :aria-expanded="isOpen"
      aria-label="Mở trợ lý mua sắm AI"
      @click="openChat"
    >
      <ChatBubbleLeftRightIcon class="size-6" aria-hidden="true" />
      <span>Hỏi trợ lý</span>
    </button>
  </div>
</template>

<style scoped>
.ai-chat-layer {
  position: fixed;
  right: 1.5rem;
  bottom: 1.5rem;
  z-index: 60;
}

.ai-chat-launcher {
  display: inline-flex;
  min-height: 3.25rem;
  align-items: center;
  gap: 0.55rem;
  border: 0;
  border-radius: 0.85rem;
  padding-inline: 1rem;
  color: white;
  background: #c8452d;
  box-shadow: 0 14px 34px rgb(23 59 53 / 20%);
  font-size: 0.875rem;
  font-weight: 850;
  transition:
    transform 180ms ease-out,
    background-color 180ms ease-out,
    box-shadow 180ms ease-out;
}

.ai-chat-launcher:hover {
  background: #a93622;
  box-shadow: 0 16px 38px rgb(23 59 53 / 25%);
  transform: translateY(-2px);
}

.ai-chat-launcher:focus-visible {
  outline: 3px solid rgb(242 193 78 / 85%);
  outline-offset: 3px;
}

.ai-chat-panel {
  position: relative;
  z-index: 1;
  display: flex;
  width: min(31.5rem, calc(100vw - 2rem));
  height: min(46rem, calc(100dvh - 3rem));
  flex-direction: column;
  overflow: hidden;
  border-radius: 1rem;
  background: #fffdf8;
  box-shadow: 0 22px 55px rgb(11 42 37 / 24%);
}

.ai-chat-header {
  display: flex;
  min-height: 4.5rem;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  color: white;
  background: #0b2a25;
}

.ai-chat-header__mark {
  display: grid;
  width: 2.75rem;
  height: 2.75rem;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 0.75rem;
  color: #0b2a25;
  background: #f2c14e;
}

.ai-chat-header__mark svg {
  width: 1.25rem;
  height: 1.25rem;
}

.ai-chat-history {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  border-bottom: 1px solid rgb(23 59 53 / 12%);
  padding: 0.55rem 0.9rem;
  background: #fffdf8;
}

.ai-chat-history label {
  flex: 0 0 auto;
  color: #526762;
  font-size: 0.7rem;
  font-weight: 800;
}

.ai-chat-history select {
  min-width: 0;
  flex: 1;
  border: 1px solid #cad9d3;
  border-radius: 0.65rem;
  padding: 0.45rem 0.65rem;
  color: #173b35;
  background: white;
  font-size: 0.75rem;
  font-weight: 700;
}

.ai-chat-history select:focus-visible {
  outline: 3px solid rgb(232 93 63 / 26%);
  outline-offset: 1px;
}

.ai-chat-presence {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  margin-top: 0.2rem;
  color: #c7d9d3;
  font-size: 0.75rem;
  line-height: 1.2;
}

.ai-chat-presence > span {
  width: 0.45rem;
  height: 0.45rem;
  border-radius: 999px;
  background: #8fc7a7;
}

.ai-chat-presence > span.is-busy {
  background: #f2c14e;
  animation: ai-chat-status-pulse 1.2s ease-in-out infinite;
}

.ai-chat-starter {
  display: flex;
  min-height: 4rem;
  width: 100%;
  align-items: center;
  gap: 0.75rem;
  border: 0;
  border-radius: 0.875rem;
  padding: 0.65rem 0.75rem;
  color: #173b35;
  background: #fffdf8;
  box-shadow: 0 8px 24px rgb(23 59 53 / 7%);
  text-align: left;
  transition:
    color 160ms ease-out,
    background-color 160ms ease-out,
    transform 180ms cubic-bezier(0.16, 1, 0.3, 1);
}

.ai-chat-starter:hover {
  color: #0b2a25;
  background: #eef2ec;
  transform: translateX(2px);
}

.ai-chat-starter:focus-visible {
  outline: 3px solid rgb(232 93 63 / 38%);
  outline-offset: 2px;
}

.ai-chat-starter__icon {
  display: grid;
  width: 2.75rem;
  height: 2.75rem;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 0.7rem;
  color: #173b35;
  background: #e8eee9;
}

.ai-chat-starter strong,
.ai-chat-starter small {
  display: block;
}

.ai-chat-starter strong {
  font-size: 0.9rem;
  font-weight: 850;
  line-height: 1.25;
}

.ai-chat-starter small {
  margin-top: 0.2rem;
  color: #526762;
  font-size: 0.75rem;
  line-height: 1.25;
}

.ai-chat-scrim {
  display: none;
}

.ai-chat-panel:focus-visible {
  outline: 3px solid rgb(242 193 78 / 85%);
  outline-offset: 3px;
}

.ai-chat-panel-enter-active,
.ai-chat-panel-leave-active {
  transition:
    opacity 180ms ease-out,
    transform 220ms cubic-bezier(0.16, 1, 0.3, 1),
    filter 180ms ease-out;
}

.ai-chat-panel-enter-from,
.ai-chat-panel-leave-to {
  opacity: 0;
  filter: blur(3px);
  transform: translateY(1rem) scale(0.985);
}

@media (max-width: 639px) {
  .ai-chat-layer {
    right: 0.75rem;
    bottom: calc(5.25rem + env(safe-area-inset-bottom));
  }

  .ai-chat-panel {
    position: fixed;
    inset: 0;
    width: 100vw;
    height: 100dvh;
    border-radius: 0;
  }

  .ai-chat-scrim {
    display: none;
  }

  .ai-chat-header {
    padding-top: calc(0.75rem + env(safe-area-inset-top));
  }

  .ai-chat-launcher span {
    display: none;
  }

  .ai-chat-launcher {
    width: 3.25rem;
    justify-content: center;
    padding: 0;
  }
}

@keyframes ai-chat-status-pulse {
  0%,
  100% {
    opacity: 0.5;
    transform: scale(0.85);
  }
  50% {
    opacity: 1;
    transform: scale(1);
  }
}

@media (prefers-reduced-motion: reduce) {
  .ai-chat-launcher,
  .ai-chat-panel-enter-active,
  .ai-chat-panel-leave-active {
    transition: none;
  }

  .ai-chat-presence > span.is-busy {
    animation: none;
  }
}
</style>
