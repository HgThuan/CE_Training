<script setup lang="ts">
import { InformationCircleIcon } from '@heroicons/vue/24/outline'
import { computed } from 'vue'

import { parseAssistantText } from '../rich-text'
import ChatInlineText from './ChatInlineText.vue'

const props = defineProps<{ content: string }>()
const blocks = computed(() => parseAssistantText(props.content))
</script>

<template>
  <div class="chat-rich-text">
    <template v-for="(block, blockIndex) in blocks" :key="`${block.type}-${blockIndex}`">
      <h3 v-if="block.type === 'heading'">
        <ChatInlineText :parts="block.content" />
      </h3>
      <aside v-else-if="block.type === 'note'" class="chat-rich-text__note" role="note">
        <InformationCircleIcon aria-hidden="true" />
        <p><ChatInlineText :parts="block.content" /></p>
      </aside>
      <component :is="block.ordered ? 'ol' : 'ul'" v-else-if="block.type === 'list'">
        <li v-for="(item, itemIndex) in block.items" :key="itemIndex">
          <ChatInlineText :parts="item.content" />
          <ul v-if="item.children.length">
            <li v-for="(child, childIndex) in item.children" :key="childIndex">
              <ChatInlineText :parts="child" />
            </li>
          </ul>
        </li>
      </component>
      <p v-else><ChatInlineText :parts="block.content" /></p>
    </template>
  </div>
</template>

<style scoped>
.chat-rich-text {
  color: #193b35;
  font-size: 1rem;
  line-height: 1.62;
  overflow-wrap: anywhere;
}

.chat-rich-text > * + * {
  margin-top: 1rem;
}

.chat-rich-text h3 {
  color: #0b2a25;
  font-size: 1.0625rem;
  font-weight: 850;
  letter-spacing: -0.015em;
  line-height: 1.45;
}

.chat-rich-text :deep(strong) {
  color: #0b2a25;
  font-weight: 800;
}

.chat-rich-text :deep(em) {
  color: #405b55;
}

.chat-rich-text :deep(code) {
  border-radius: 0.35rem;
  background: #e8eee9;
  padding: 0.1rem 0.3rem;
  color: #0b2a25;
  font-size: 0.875em;
}

.chat-rich-text ul,
.chat-rich-text ol {
  margin-top: 0.15rem;
  padding-left: 1.25rem;
}

.chat-rich-text ul {
  list-style: disc;
}

.chat-rich-text ol {
  list-style: decimal;
}

.chat-rich-text li {
  padding-left: 0.2rem;
}

.chat-rich-text li + li {
  margin-top: 0.55rem;
}

.chat-rich-text li::marker {
  color: #c8452d;
  font-weight: 800;
}

.chat-rich-text li > ul {
  display: grid;
  gap: 0.4rem;
  margin-top: 0.55rem;
  padding-left: 0;
  list-style: none;
}

.chat-rich-text li > ul > li {
  border-radius: 0.55rem;
  padding: 0.45rem 0.6rem;
  color: #35524c;
  background: #edf1ec;
  font-size: 0.9rem;
  line-height: 1.5;
}

.chat-rich-text__note {
  display: grid;
  grid-template-columns: 1.15rem minmax(0, 1fr);
  gap: 0.55rem;
  border-radius: 0.75rem;
  background: #fff0ea;
  padding: 0.8rem;
  color: #713424;
  font-size: 0.8125rem;
  line-height: 1.6;
}

.chat-rich-text__note > svg {
  width: 1.15rem;
  height: 1.15rem;
  margin-top: 0.12rem;
  color: #c8452d;
}
</style>
