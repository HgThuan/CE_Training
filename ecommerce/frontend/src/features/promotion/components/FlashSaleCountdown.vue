<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'

const props = defineProps<{ endTime: string }>()
const emit = defineEmits<{ ended: [] }>()

// The API does not expose server_time yet, so this countdown uses the client clock.
const now = ref(Date.now())
const remaining = computed(() => Math.max(0, new Date(props.endTime).getTime() - now.value))
const ended = computed(() => remaining.value === 0)
const label = computed(() => {
  if (ended.value) return 'Đã kết thúc'
  const totalSeconds = Math.floor(remaining.value / 1000)
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  return [hours, minutes, seconds].map((value) => String(value).padStart(2, '0')).join(':')
})

let notified = ended.value
const timer = window.setInterval(() => {
  now.value = Date.now()
  if (ended.value && !notified) {
    notified = true
    emit('ended')
  }
}, 1000)

onBeforeUnmount(() => window.clearInterval(timer))
</script>

<template>
  <span class="font-mono font-black" :class="ended ? 'text-slate-400' : 'text-amber-300'">{{
    label
  }}</span>
</template>
