<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { accountApi } from '@/features/account/api'
import type { Address } from '@/features/account/types'
import { orderApi } from '@/features/order/api'
import type { CheckoutPreview } from '@/features/order/types'
import { formatCurrency } from '@/shared/lib/formatters'

const router = useRouter()
const addresses = ref<Address[]>([])
const addressId = ref<number | null>(null)
const paymentMethod = ref<'COD' | 'VNPAY'>('COD')
const platformCoupon = ref('')
const preview = ref<CheckoutPreview | null>(null)
const loading = ref(false)
const submitting = ref(false)
const error = ref('')
const canSubmit = computed(() => Boolean(addressId.value && preview.value && !submitting.value))

function payload() {
  return {
    address_id: addressId.value,
    payment_method: paymentMethod.value,
    coupons: platformCoupon.value ? { platform: platformCoupon.value } : {},
  }
}

async function loadPreview(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    preview.value = (await orderApi.preview(payload())).data.data
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : 'Không thể tính checkout.'
  } finally {
    loading.value = false
  }
}

async function confirm(): Promise<void> {
  if (!canSubmit.value) return
  submitting.value = true
  error.value = ''
  try {
    const response = await orderApi.confirm(payload(), crypto.randomUUID())
    const url = response.data.data.payment_redirect_url
    if (url) window.location.assign(url)
    else await router.push(`/account/orders/${response.data.data.id}`)
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : 'Đặt hàng thất bại.'
    submitting.value = false
  }
}

onMounted(async () => {
  addresses.value = (await accountApi.listAddresses()).data.data
  addressId.value = addresses.value.find((item) => item.is_default)?.id ?? addresses.value[0]?.id ?? null
  await loadPreview()
})
</script>

<template>
  <main class="mx-auto max-w-5xl space-y-6 px-4 py-8">
    <div><p class="text-sm font-bold text-indigo-600">Checkout</p><h1 class="text-3xl font-black">Xác nhận đơn hàng</h1></div>
    <p v-if="error" class="rounded-xl bg-rose-50 p-4 text-rose-700">{{ error }}</p>
    <section class="grid gap-6 lg:grid-cols-[1fr_340px]">
      <div class="space-y-5">
        <div class="rounded-2xl bg-white p-5 shadow-sm"><h2 class="mb-3 font-black">Địa chỉ giao hàng</h2>
          <select v-model="addressId" class="w-full rounded-xl border p-3" @change="loadPreview">
            <option v-for="address in addresses" :key="address.id" :value="address.id">{{ address.recipient_name }} — {{ address.detail_address }}</option>
          </select></div>
        <div class="rounded-2xl bg-white p-5 shadow-sm"><h2 class="mb-3 font-black">Thanh toán</h2>
          <label class="mr-6"><input v-model="paymentMethod" value="COD" type="radio"> COD</label>
          <label><input v-model="paymentMethod" value="VNPAY" type="radio"> VNPay Sandbox</label></div>
        <div class="rounded-2xl bg-white p-5 shadow-sm"><h2 class="mb-3 font-black">Voucher sàn</h2>
          <div class="flex gap-2"><input v-model.trim="platformCoupon" class="flex-1 rounded-xl border p-3" placeholder="Nhập mã voucher"><button class="rounded-xl bg-slate-900 px-4 text-white" @click="loadPreview">Áp dụng</button></div></div>
        <div v-if="preview" class="space-y-3"><article v-for="shop in preview.shops" :key="shop.shop_id" class="rounded-2xl bg-white p-5 shadow-sm">
          <h3 class="font-black">{{ shop.shop_name }}</h3><p>Tạm tính: {{ formatCurrency(shop.subtotal) }}</p><p>Phí ship: {{ formatCurrency(shop.shipping_fee) }}</p><p class="font-bold">Tổng shop: {{ formatCurrency(shop.total) }}</p>
        </article></div>
      </div>
      <aside class="h-fit rounded-2xl bg-slate-950 p-6 text-white lg:sticky lg:top-24"><h2 class="text-xl font-black">Tổng thanh toán</h2>
        <template v-if="preview"><p class="mt-4 flex justify-between"><span>Hàng hóa</span><b>{{ formatCurrency(preview.subtotal) }}</b></p><p class="mt-2 flex justify-between"><span>Giảm giá</span><b>-{{ formatCurrency(preview.discount) }}</b></p><p class="mt-2 flex justify-between"><span>Vận chuyển</span><b>{{ formatCurrency(preview.shipping_total) }}</b></p><p class="mt-5 flex justify-between border-t border-slate-700 pt-4 text-xl"><span>Tổng</span><b>{{ formatCurrency(preview.total) }}</b></p></template>
        <button class="mt-6 w-full rounded-xl bg-indigo-500 py-3 font-black disabled:opacity-50" :disabled="!canSubmit" @click="confirm">{{ submitting ? 'Đang đặt hàng…' : 'Đặt hàng' }}</button>
        <p v-if="loading" class="mt-3 text-sm text-slate-300">Đang cập nhật giá…</p></aside>
    </section>
  </main>
</template>
