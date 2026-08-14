<script setup lang="ts">
import { RouterView } from 'vue-router'

import CustomerAppHeader from '@/shared/components/CustomerAppHeader.vue'
</script>

<template>
  <div class="market-app-shell">
    <CustomerAppHeader />
    <RouterView />
  </div>
</template>
