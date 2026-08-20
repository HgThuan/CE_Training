<script setup lang="ts">
import { RouterView } from 'vue-router'

import ChatWidget from '@/features/ai-chat/components/ChatWidget.vue'
import ProductCompareBar from '@/features/product/components/ProductCompareBar.vue'
import CustomerAccountNavigation from '@/shared/components/CustomerAccountNavigation.vue'
import CustomerAppFooter from '@/shared/components/CustomerAppFooter.vue'
import CustomerAppHeader from '@/shared/components/CustomerAppHeader.vue'
</script>

<template>
  <div class="market-app-shell">
    <a class="app-skip-link" href="#customer-account-main">Đi đến nội dung chính</a>
    <CustomerAppHeader />
    <div class="customer-account-shell">
      <CustomerAccountNavigation />
      <div id="customer-account-main" class="customer-account-content" tabindex="-1">
        <RouterView />
      </div>
    </div>
    <CustomerAppFooter />
    <ProductCompareBar />
    <ChatWidget />
  </div>
</template>
