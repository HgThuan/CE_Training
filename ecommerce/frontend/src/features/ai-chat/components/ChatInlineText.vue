<script setup lang="ts">
import type { InlinePart } from '../rich-text'

defineProps<{ parts: InlinePart[] }>()
</script>

<template>
  <template v-for="(part, index) in parts" :key="`${part.type}-${index}`">
    <strong v-if="part.type === 'strong'">{{ part.text }}</strong>
    <em v-else-if="part.type === 'emphasis'">{{ part.text }}</em>
    <code v-else-if="part.type === 'code'">{{ part.text }}</code>
    <span v-else>{{ part.text }}</span>
  </template>
</template>
