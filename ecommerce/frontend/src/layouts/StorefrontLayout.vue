<script setup lang="ts">
import { RouterView } from 'vue-router'

import ProductCompareBar from '@/features/product/components/ProductCompareBar.vue'
import CustomerAppHeader from '@/shared/components/CustomerAppHeader.vue'
</script>

<template>
  <div class="market-app-shell">
    <CustomerAppHeader />
    <RouterView />
    <ProductCompareBar />
  </div>
</template>
