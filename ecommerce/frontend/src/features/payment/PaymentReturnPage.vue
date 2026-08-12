<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { orderApi } from '@/features/order/api'
const route=useRoute(), state=ref('Đang xác minh thanh toán…'), orderId=ref(String(route.query.order_id||''))
onMounted(async()=>{try{if(route.query.vnp_SecureHash){const params=Object.fromEntries(Object.entries(route.query).map(([key,value])=>[key,String(Array.isArray(value)?value[0]??'':value??'')]));const callback=await orderApi.verifyVnpayReturn(params);orderId.value=String(callback.data.order_id||orderId.value)}if(!orderId.value){state.value='Không xác định được đơn hàng.';return}const response=await orderApi.paymentStatus(orderId.value);state.value=`Trạng thái thanh toán: ${response.data.data.payment_status}`}catch{state.value='Không thể xác minh thanh toán. Vui lòng xem trong đơn hàng.'}})
</script>
<template><main class="mx-auto max-w-xl px-4 py-20 text-center"><h1 class="text-3xl font-black">Kết quả VNPay</h1><p class="mt-4 text-lg">{{ state }}</p><RouterLink class="mt-6 inline-block rounded-xl bg-indigo-600 px-5 py-3 font-bold text-white" to="/account/orders">Xem đơn hàng</RouterLink></main></template>
