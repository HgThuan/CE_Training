<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { formatCurrency } from '@/shared/lib/formatters'
import { orderApi } from '@/features/order/api'
import type { ShopOrder } from '@/features/order/types'
const orders=ref<ShopOrder[]>([]),loading=ref(true),error=ref('')
const actionMap:Record<string,string[]>={PENDING_CONFIRMATION:['confirm','cancel'],CONFIRMED:['pack','cancel'],PACKING:['ship','cancel'],SHIPPING:['complete']}
async function load(){loading.value=true;try{orders.value=(await orderApi.sellerOrders()).data.data}catch{error.value='Không thể tải đơn của shop.'}finally{loading.value=false}}
async function act(item:ShopOrder,action:string){let reason='';if(action==='cancel'){reason=prompt('Lý do hủy đơn:')||'';if(!reason)return}await orderApi.sellerAction(item.id,action,reason);await load()}
async function printPackingSlip(item:ShopOrder){const popup=window.open('', '_blank');try{const response=await orderApi.packingSlip(item.id);const url=URL.createObjectURL(new Blob([response.data],{type:'text/html;charset=utf-8'}));if(popup)popup.location.href=url;else window.open(url,'_blank');window.setTimeout(()=>URL.revokeObjectURL(url),60000)}catch{popup?.close();error.value='Không thể tải phiếu đóng gói.'}}
onMounted(load)
</script>
<template><main class="mx-auto max-w-7xl px-4 py-8"><h1 class="text-3xl font-black">Xử lý đơn hàng</h1><p class="mt-1 text-slate-500">Mỗi đơn chỉ thuộc gian hàng đang đăng nhập.</p><p v-if="loading" class="mt-6">Đang tải…</p><p v-else-if="error" class="mt-6 text-rose-700">{{ error }}</p><div v-else class="mt-6 overflow-x-auto rounded-2xl bg-white shadow-sm"><table class="w-full text-left"><thead class="bg-slate-100"><tr><th class="p-4">Mã đơn</th><th>Khách</th><th>Trạng thái</th><th>Tổng</th><th>Thao tác</th></tr></thead><tbody><tr v-for="item in orders" :key="item.id" class="border-t"><td class="p-4 font-mono font-bold">{{ item.shop_order_code }}</td><td>{{ item.customer_email }}</td><td>{{ item.fulfillment_status }}</td><td>{{ formatCurrency(item.total_amount) }}</td><td class="space-x-2"><button v-for="action in actionMap[item.fulfillment_status]||[]" :key="action" class="rounded-lg border px-3 py-2 text-sm font-bold" @click="act(item,action)">{{ action }}</button><button class="rounded-lg border px-3 py-2 text-sm font-bold" @click="printPackingSlip(item)">In phiếu</button></td></tr></tbody></table></div></main></template>
