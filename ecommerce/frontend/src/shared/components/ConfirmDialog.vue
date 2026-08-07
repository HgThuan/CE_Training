<script setup lang="ts">
import { ExclamationTriangleIcon } from '@heroicons/vue/24/outline'
import { onMounted, onUnmounted, ref, watch } from 'vue'

interface Props {
  open: boolean
  title?: string
  message?: string
  confirmText?: string
  cancelText?: string
  variant?: 'danger' | 'warning' | 'info'
}

const props = withDefaults(defineProps<Props>(), {
  title: 'Xác nhận',
  message: 'Bạn có chắc chắn muốn thực hiện thao tác này?',
  confirmText: 'Xác nhận',
  cancelText: 'Hủy',
  variant: 'danger',
})

const emit = defineEmits<{
  (e: 'confirm'): void
  (e: 'cancel'): void
}>()

const dialogRef = ref<HTMLDivElement | null>(null)

const variantClasses = {
  danger: {
    icon: 'bg-rose-100 text-rose-600',
    button: 'bg-rose-600 hover:bg-rose-700 focus-visible:ring-rose-500',
  },
  warning: {
    icon: 'bg-amber-100 text-amber-600',
    button: 'bg-amber-600 hover:bg-amber-700 focus-visible:ring-amber-500',
  },
  info: {
    icon: 'bg-indigo-100 text-indigo-600',
    button: 'bg-indigo-600 hover:bg-indigo-700 focus-visible:ring-indigo-500',
  },
}

function handleKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape') {
    emit('cancel')
  }
}

watch(
  () => props.open,
  (isOpen) => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
  },
)

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
  document.body.style.overflow = ''
})
</script>

<template>
  <Teleport to="body">
    <Transition name="confirm-dialog">
      <div
        v-if="open"
        ref="dialogRef"
        class="confirm-dialog-overlay"
        role="dialog"
        aria-modal="true"
        :aria-label="title"
        @click.self="emit('cancel')"
      >
        <div class="confirm-dialog-panel">
          <div class="confirm-dialog-body">
            <div class="confirm-dialog-icon" :class="variantClasses[variant].icon">
              <ExclamationTriangleIcon class="h-6 w-6" />
            </div>
            <div class="confirm-dialog-content">
              <h3 class="confirm-dialog-title">{{ title }}</h3>
              <p class="confirm-dialog-message">{{ message }}</p>
            </div>
          </div>
          <div class="confirm-dialog-actions">
            <button
              class="confirm-dialog-btn confirm-dialog-btn--cancel"
              type="button"
              @click="emit('cancel')"
            >
              {{ cancelText }}
            </button>
            <button
              class="confirm-dialog-btn confirm-dialog-btn--confirm"
              :class="variantClasses[variant].button"
              type="button"
              @click="emit('confirm')"
            >
              {{ confirmText }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.confirm-dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: grid;
  place-items: center;
  padding: 1rem;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(4px);
}

.confirm-dialog-panel {
  width: 100%;
  max-width: 28rem;
  overflow: hidden;
  border-radius: 1.25rem;
  background: #fff;
  box-shadow:
    0 20px 25px -5px rgba(0, 0, 0, 0.1),
    0 8px 10px -6px rgba(0, 0, 0, 0.1);
}

.confirm-dialog-body {
  display: flex;
  gap: 1rem;
  padding: 1.5rem;
}

.confirm-dialog-icon {
  display: grid;
  place-items: center;
  width: 2.75rem;
  height: 2.75rem;
  flex-shrink: 0;
  border-radius: 0.75rem;
}

.confirm-dialog-content {
  min-width: 0;
  flex: 1;
}

.confirm-dialog-title {
  font-size: 1.05rem;
  font-weight: 900;
  color: #0f172a;
  line-height: 1.4;
}

.confirm-dialog-message {
  margin-top: 0.375rem;
  font-size: 0.875rem;
  color: #64748b;
  line-height: 1.6;
}

.confirm-dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.625rem;
  padding: 0.75rem 1.5rem;
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
}

.confirm-dialog-btn {
  padding: 0.5rem 1.25rem;
  border-radius: 0.75rem;
  font-size: 0.875rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
  border: none;
}

.confirm-dialog-btn--cancel {
  background: #fff;
  color: #475569;
  border: 1px solid #cbd5e1;
}

.confirm-dialog-btn--cancel:hover {
  background: #f1f5f9;
}

.confirm-dialog-btn--confirm {
  color: #fff;
}

.confirm-dialog-btn--confirm:focus-visible {
  outline: 2px solid transparent;
  outline-offset: 2px;
  box-shadow: 0 0 0 2px #fff, 0 0 0 4px currentColor;
}

/* Transition */
.confirm-dialog-enter-active {
  transition: opacity 0.2s ease;
}

.confirm-dialog-enter-active .confirm-dialog-panel {
  transition:
    opacity 0.2s ease,
    transform 0.2s ease;
}

.confirm-dialog-leave-active {
  transition: opacity 0.15s ease;
}

.confirm-dialog-leave-active .confirm-dialog-panel {
  transition:
    opacity 0.15s ease,
    transform 0.15s ease;
}

.confirm-dialog-enter-from {
  opacity: 0;
}

.confirm-dialog-enter-from .confirm-dialog-panel {
  opacity: 0;
  transform: scale(0.95) translateY(8px);
}

.confirm-dialog-leave-to {
  opacity: 0;
}

.confirm-dialog-leave-to .confirm-dialog-panel {
  opacity: 0;
  transform: scale(0.95) translateY(8px);
}
</style>
