<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { orderApi } from '@/features/order/api'
const route=useRoute(), state=ref('Đang xác minh thanh toán…'), orderId=String(route.query.order_id||route.query.vnp_OrderInfo||'')
onMounted(async()=>{if(!orderId){state.value='Không xác định được đơn hàng.';return}try{const response=await orderApi.paymentStatus(orderId);state.value=`Trạng thái thanh toán: ${response.data.data.payment_status}`}catch{state.value='Không thể xác minh thanh toán. Vui lòng xem trong đơn hàng.'}})
</script>
<template><main class="mx-auto max-w-xl px-4 py-20 text-center"><h1 class="text-3xl font-black">Kết quả VNPay</h1><p class="mt-4 text-lg">{{ state }}</p><RouterLink class="mt-6 inline-block rounded-xl bg-indigo-600 px-5 py-3 font-bold text-white" to="/account/orders">Xem đơn hàng</RouterLink></main></template>
