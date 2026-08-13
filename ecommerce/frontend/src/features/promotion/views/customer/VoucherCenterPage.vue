<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

import { promotionApi } from '../../api'
import VoucherCard from '../../components/VoucherCard.vue'
import type { Voucher } from '../../types'

const auth = useAuthStore()
const router = useRouter()
const vouchers = ref<Voucher[]>([])
const loading = ref(true)
const collecting = ref(new Set<string>())
const notice = ref('')
const error = ref('')

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    vouchers.value = (await promotionApi.voucherCenter()).data.data
  } catch {
    error.value = 'Không thể tải trung tâm voucher.'
  } finally {
    loading.value = false
  }
}

async function collect(voucher: Voucher): Promise<void> {
  if (!auth.isAuthenticated) {
    await router.push({ name: 'login', query: { redirect: '/voucher-center' } })
    return
  }
  voucher.is_collected = true
  collecting.value.add(voucher.id)
  error.value = ''
  try {
    await promotionApi.collectVoucher(voucher.id, crypto.randomUUID())
    notice.value = `Đã lưu voucher ${voucher.code}.`
  } catch {
    voucher.is_collected = false
    error.value = 'Không thể lưu voucher; voucher có thể vừa hết hoặc bạn đã đạt giới hạn.'
  } finally {
    collecting.value.delete(voucher.id)
  }
}

onMounted(() => void load())
</script>

<template>
  <main class="mx-auto min-h-[70vh] max-w-7xl px-4 py-10 sm:px-6">
    <p class="text-sm font-black uppercase tracking-widest text-indigo-600">Ưu đãi dành cho bạn</p>
    <h1 class="mt-2 text-4xl font-black">Trung tâm Voucher</h1>
    <div class="mt-5 flex gap-3">
      <RouterLink
        v-if="auth.user?.role === 'customer'"
        class="rounded-xl border px-4 py-2 text-sm font-bold"
        to="/me/vouchers"
      >
        Voucher của tôi
      </RouterLink>
    </div>
    <p v-if="notice" class="mt-5 rounded-xl bg-emerald-50 p-3 font-bold text-emerald-700">
      {{ notice }}
    </p>
    <p v-if="error" class="mt-5 rounded-xl bg-rose-50 p-3 font-bold text-rose-700">
      {{ error }}
    </p>
    <div v-if="loading" class="mt-8 grid gap-4 md:grid-cols-2">
      <div v-for="index in 4" :key="index" class="h-40 animate-pulse rounded-2xl bg-slate-200" />
    </div>
    <div v-else class="mt-8 grid gap-4 md:grid-cols-2">
      <VoucherCard
        v-for="voucher in vouchers"
        :key="voucher.id"
        :voucher="voucher"
        :collected="voucher.is_collected"
        :loading="collecting.has(voucher.id)"
        @collect="collect"
      />
    </div>
  </main>
</template>
