<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { orderApi } from '@/features/order/api'
const route = useRoute(),
  state = ref('Đang xác minh thanh toán…'),
  orderId = ref(String(route.query.order_id || ''))

onMounted(async () => {
  if (route.query.vnp_SecureHash) {
    try {
      const params = Object.fromEntries(
        Object.entries(route.query).map(([key, value]) => [
          key,
          String(Array.isArray(value) ? (value[0] ?? '') : (value ?? '')),
        ]),
      )
      const callback = await orderApi.verifyVnpayReturn(params)
      orderId.value = String(callback.data.order_id || orderId.value)
    } catch {
      // The server-side IPN may already have updated the order; poll as a fallback.
    }
  }

  if (!orderId.value) orderId.value = localStorage.getItem('last_payment_order_id') || ''
  if (!orderId.value) {
    state.value = 'Không xác định được đơn hàng.'
    return
  }

  let attempts = 0
  const checkStatus = async () => {
    try {
      const response = await orderApi.paymentStatus(orderId.value)
      const status = response.data.data.payment_status
      if (status === 'PENDING' && attempts < 5) {
        attempts += 1
        window.setTimeout(checkStatus, 2000)
        return
      }
      state.value = `Trạng thái thanh toán: ${status === 'PAID' ? 'Thành công' : status}`
      localStorage.removeItem('last_payment_order_id')
    } catch {
      state.value = 'Không thể xác minh thanh toán. Vui lòng xem trong đơn hàng.'
    }
  }

  await checkStatus()
})
</script>
<template>
  <main class="mx-auto max-w-xl px-4 py-20 text-center">
    <h1 class="text-3xl font-black">Kết quả VNPay</h1>
    <p class="mt-4 text-lg">{{ state }}</p>
    <RouterLink
      class="mt-6 inline-block rounded-xl bg-indigo-600 px-5 py-3 font-bold text-white"
      to="/account/orders"
    >
      Xem đơn hàng
    </RouterLink>
  </main>
</template>
