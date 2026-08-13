<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  platformCode: string
  shopCodes: Record<string, string>
  shops: Array<{ shop_id: number; shop_name: string }>
  loading?: boolean
  error?: string
}>()

const emit = defineEmits<{
  'update:platformCode': [value: string]
  'update:shopCode': [shopId: string, value: string]
  apply: []
}>()

const normalizedPlatform = computed({
  get: () => props.platformCode,
  set: (value: string) => emit('update:platformCode', value.toUpperCase()),
})
</script>

<template>
  <section class="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
    <h2 class="text-lg font-black text-slate-950">Voucher</h2>
    <p class="mt-1 text-sm text-slate-500">Có thể dùng một mã sàn và một mã riêng cho mỗi shop.</p>
    <div class="mt-4 grid gap-3 md:grid-cols-2">
      <label class="text-sm font-bold text-slate-700">
        Voucher sàn
        <input
          v-model="normalizedPlatform"
          class="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 font-mono uppercase focus:border-indigo-500 focus:outline-none"
          placeholder="VD: PLATFORM50"
        />
      </label>
      <label v-for="shop in shops" :key="shop.shop_id" class="text-sm font-bold text-slate-700">
        {{ shop.shop_name }}
        <input
          :value="shopCodes[String(shop.shop_id)] ?? ''"
          class="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 font-mono uppercase focus:border-indigo-500 focus:outline-none"
          placeholder="Voucher của shop"
          @input="
            emit(
              'update:shopCode',
              String(shop.shop_id),
              ($event.target as HTMLInputElement).value.toUpperCase(),
            )
          "
        />
      </label>
    </div>
    <p v-if="error" class="mt-3 rounded-xl bg-rose-50 px-3 py-2 text-sm font-bold text-rose-700">
      {{ error }}
    </p>
    <button
      class="mt-4 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-bold text-white hover:bg-indigo-700 disabled:opacity-50"
      type="button"
      :disabled="loading"
      @click="emit('apply')"
    >
      {{ loading ? 'Đang tính...' : 'Áp dụng và xem giá' }}
    </button>
  </section>
</template>
