<script setup lang="ts">
import { RouterView } from 'vue-router'

import ChatWidget from '@/features/ai-chat/components/ChatWidget.vue'
import ProductCompareBar from '@/features/product/components/ProductCompareBar.vue'
import CustomerAppHeader from '@/shared/components/CustomerAppHeader.vue'
</script>

<template>
  <div class="market-app-shell">
    <CustomerAppHeader />
    <RouterView />
    <ProductCompareBar />
    <ChatWidget />
  </div>
</template>
