<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { analyticsApi } from '../api'
import type { ChartPoint, RankingRow, Summary, RevenueChartResponse } from '../types'
import RevenueChart from '../components/RevenueChart.vue'

const props = defineProps<{ mode: 'admin' | 'seller' }>()
const days = ref(30)
const period = ref<'day' | 'week' | 'month'>('day')
const loading = ref(false)
const error = ref('')
const summary = ref<Summary>({ revenue: 0, orders: 0, products: 0 })
const chart = ref<ChartPoint[]>([])
const growth = ref(0)
const products = ref<RankingRow[]>([])

async function load() {
  loading.value = true
  error.value = ''
  try {
    const calls = props.mode === 'admin'
      ? [analyticsApi.adminSummary(days.value), analyticsApi.adminRevenue(days.value, period.value), analyticsApi.adminProducts(days.value)]
      : [analyticsApi.sellerSummary(days.value), analyticsApi.sellerRevenue(days.value, period.value), analyticsApi.sellerProducts(days.value)]
    const [summaryResponse, chartResponse, productResponse] = await Promise.all(calls)
    summary.value = summaryResponse.data.data as Summary
    const chartData = chartResponse.data.data as RevenueChartResponse
    chart.value = chartData.chart
    growth.value = chartData.growth
    products.value = productResponse.data.data as RankingRow[]
  } catch { error.value = 'Không thể tải dashboard. Vui lòng thử lại.' } finally { loading.value = false }
}

watch([days, period], load)
onMounted(load)
</script>

<template>
  <main class="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6">
    <div class="flex flex-wrap items-end justify-between gap-4">
      <div><p class="text-sm font-bold uppercase tracking-widest text-indigo-600">Analytics</p><h1 class="text-3xl font-black text-slate-950">{{ mode === 'admin' ? 'Tổng quan toàn sàn' : (summary.shop_name || 'Tổng quan gian hàng') }}</h1></div>
      <div class="flex items-center gap-2">
        <select v-model="period" class="rounded-xl border border-slate-300 bg-white px-4 py-2 font-semibold">
          <option value="day">Theo ngày</option>
          <option value="week">Theo tuần</option>
          <option value="month">Theo tháng</option>
        </select>
        <select v-model.number="days" class="rounded-xl border border-slate-300 bg-white px-4 py-2 font-semibold">
          <option :value="7">7 ngày qua</option>
          <option :value="30">30 ngày qua</option>
          <option :value="90">90 ngày qua</option>
        </select>
      </div>
    </div>
    <p v-if="error" class="rounded-xl bg-rose-50 p-4 text-rose-700">{{ error }}</p>
    <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4" :class="{ 'opacity-60': loading }">
      <article v-for="card in [{ label: 'Doanh thu', value: `${Number(summary.revenue).toLocaleString('vi-VN')} ₫` }, { label: 'Đơn hàng', value: summary.orders }, { label: mode === 'admin' ? 'Khách mới' : 'Chờ xác nhận', value: mode === 'admin' ? summary.customers : summary.pending_orders }, { label: 'Sản phẩm', value: summary.products }]" :key="card.label" class="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200"><p class="text-sm font-semibold text-slate-500">{{ card.label }}</p><p class="mt-2 text-2xl font-black text-slate-950">{{ card.value ?? 0 }}</p></article>
    </div>
    <section class="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
      <div class="mb-6 flex flex-wrap items-center justify-between gap-4">
        <h2 class="text-lg font-black">Biểu đồ doanh thu</h2>
        <div v-if="!loading" class="flex items-center gap-2 rounded-full px-3 py-1 text-sm font-bold" :class="growth >= 0 ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'">
          <span v-if="growth >= 0">▲</span><span v-else>▼</span>
          {{ Math.abs(growth) }}% <span class="font-normal opacity-70">so với kỳ trước</span>
        </div>
      </div>
      <RevenueChart :points="chart" />
    </section>
    <section class="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200"><h2 class="mb-4 text-lg font-black">Sản phẩm bán chạy</h2><div class="divide-y"><div v-for="(item, index) in products" :key="String(item.product_id)" class="flex justify-between py-3"><span><b class="mr-3 text-indigo-600">#{{ index + 1 }}</b>{{ item.product_name }}</span><span class="font-bold">{{ item.quantity }} sản phẩm · {{ Number(item.revenue).toLocaleString('vi-VN') }} ₫</span></div><p v-if="!products.length" class="py-6 text-center text-slate-500">Chưa có dữ liệu.</p></div></section>
  </main>
</template>
