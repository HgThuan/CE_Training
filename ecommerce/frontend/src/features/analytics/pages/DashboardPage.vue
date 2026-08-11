<script setup lang="ts">
import {
  ArrowPathIcon,
  BanknotesIcon,
  CubeIcon,
  ShoppingBagIcon,
  UserPlusIcon,
} from '@heroicons/vue/24/outline'
import { computed, onMounted, ref, watch } from 'vue'

import RevenueChart from '../components/RevenueChart.vue'
import { analyticsApi } from '../api'
import type { ChartPoint, RankingRow, RevenueChartResponse, Summary } from '../types'

const props = defineProps<{ mode: 'admin' | 'seller' }>()
const days = ref(30)
const period = ref<'day' | 'week' | 'month'>('day')
const loading = ref(false)
const error = ref('')
const summary = ref<Summary>({ revenue: 0, orders: 0, products: 0 })
const chart = ref<ChartPoint[]>([])
const growth = ref(0)
const products = ref<RankingRow[]>([])

const currencyFormatter = new Intl.NumberFormat('vi-VN', {
  style: 'currency',
  currency: 'VND',
  maximumFractionDigits: 0,
})
const numberFormatter = new Intl.NumberFormat('vi-VN')

const metricCards = computed(() => [
  {
    label: 'Doanh thu',
    value: currencyFormatter.format(Number(summary.value.revenue || 0)),
    helper: `Trong ${days.value} ngày gần nhất`,
    icon: BanknotesIcon,
    iconClass: 'bg-emerald-50 text-emerald-700 ring-emerald-100',
  },
  {
    label: 'Đơn hàng',
    value: numberFormatter.format(summary.value.orders || 0),
    helper: 'Đơn hàng đã ghi nhận',
    icon: ShoppingBagIcon,
    iconClass: 'bg-sky-50 text-sky-700 ring-sky-100',
  },
  {
    label: props.mode === 'admin' ? 'Khách hàng mới' : 'Chờ xác nhận',
    value: numberFormatter.format(
      props.mode === 'admin' ? summary.value.customers || 0 : summary.value.pending_orders || 0,
    ),
    helper: props.mode === 'admin' ? 'Tài khoản mới trong kỳ' : 'Đơn cần xử lý',
    icon: UserPlusIcon,
    iconClass: 'bg-violet-50 text-violet-700 ring-violet-100',
  },
  {
    label: 'Sản phẩm',
    value: numberFormatter.format(summary.value.products || 0),
    helper: props.mode === 'admin' ? 'Đang có trên toàn sàn' : 'Trong danh mục của bạn',
    icon: CubeIcon,
    iconClass: 'bg-amber-50 text-amber-700 ring-amber-100',
  },
])

const periodLabel = computed(() => {
  const labels = { day: 'ngày', week: 'tuần', month: 'tháng' }
  return `Dữ liệu theo ${labels[period.value]} trong ${days.value} ngày gần nhất`
})

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const calls =
      props.mode === 'admin'
        ? [
            analyticsApi.adminSummary(days.value),
            analyticsApi.adminRevenue(days.value, period.value),
            analyticsApi.adminProducts(days.value),
          ]
        : [
            analyticsApi.sellerSummary(days.value),
            analyticsApi.sellerRevenue(days.value, period.value),
            analyticsApi.sellerProducts(days.value),
          ]
    const [summaryResponse, chartResponse, productResponse] = await Promise.all(calls)
    summary.value = summaryResponse.data.data as Summary
    const chartData = chartResponse.data.data as RevenueChartResponse
    chart.value = chartData.chart
    growth.value = chartData.growth
    products.value = productResponse.data.data as RankingRow[]
  } catch {
    error.value = 'Không thể tải dữ liệu dashboard. Vui lòng thử lại.'
  } finally {
    loading.value = false
  }
}

watch([days, period], load)
onMounted(load)
</script>

<template>
  <div class="mx-auto max-w-[1440px] space-y-6" :aria-busy="loading">
    <header class="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
      <div>
        <p class="mb-1 text-xs font-bold uppercase tracking-[0.18em] text-indigo-600">
          {{ mode === 'admin' ? 'Trung tâm điều hành' : 'Phân tích bán hàng' }}
        </p>
        <h1 class="text-2xl font-black tracking-tight text-slate-950 sm:text-3xl">
          {{ mode === 'admin' ? 'Tổng quan toàn sàn' : summary.shop_name || 'Tổng quan gian hàng' }}
        </h1>
        <p class="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
          Theo dõi nhanh hiệu suất kinh doanh và những chỉ số cần chú ý.
        </p>
      </div>

      <div
        class="grid grid-cols-2 gap-2 rounded-2xl border border-slate-200 bg-white p-2 shadow-sm sm:flex"
        aria-label="Bộ lọc thời gian"
      >
        <label class="min-w-0">
          <span class="sr-only">Nhóm dữ liệu theo</span>
          <select
            v-model="period"
            class="h-10 w-full rounded-xl border-0 bg-slate-50 px-3 text-sm font-semibold text-slate-700 outline-none ring-indigo-500 transition focus:ring-2"
          >
            <option value="day">Theo ngày</option>
            <option value="week">Theo tuần</option>
            <option value="month">Theo tháng</option>
          </select>
        </label>
        <label class="min-w-0">
          <span class="sr-only">Khoảng thời gian</span>
          <select
            v-model.number="days"
            class="h-10 w-full rounded-xl border-0 bg-slate-50 px-3 text-sm font-semibold text-slate-700 outline-none ring-indigo-500 transition focus:ring-2"
          >
            <option :value="7">7 ngày qua</option>
            <option :value="30">30 ngày qua</option>
            <option :value="90">90 ngày qua</option>
          </select>
        </label>
        <button
          type="button"
          class="col-span-2 flex h-10 items-center justify-center gap-2 rounded-xl px-3 text-sm font-bold text-indigo-700 transition hover:bg-indigo-50 disabled:cursor-wait disabled:opacity-50 sm:col-span-1"
          :disabled="loading"
          @click="load"
        >
          <ArrowPathIcon class="h-4 w-4" :class="{ 'animate-spin': loading }" />
          Làm mới
        </button>
      </div>
    </header>

    <div
      v-if="error"
      role="alert"
      class="flex flex-col gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800 sm:flex-row sm:items-center sm:justify-between"
    >
      <span>{{ error }}</span>
      <button type="button" class="font-bold underline underline-offset-4" @click="load">
        Thử lại
      </button>
    </div>

    <section aria-label="Chỉ số tổng quan" class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <article
        v-for="card in metricCards"
        :key="card.label"
        class="relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition duration-200 hover:-translate-y-0.5 hover:shadow-md"
      >
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0">
            <p class="text-sm font-semibold text-slate-500">{{ card.label }}</p>
            <div
              v-if="loading && !error"
              class="mt-3 h-8 w-28 animate-pulse rounded-lg bg-slate-100"
            />
            <p v-else class="mt-2 truncate text-2xl font-black tracking-tight text-slate-950">
              {{ card.value }}
            </p>
          </div>
          <span
            class="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ring-1 ring-inset"
            :class="card.iconClass"
          >
            <component :is="card.icon" class="h-5 w-5" aria-hidden="true" />
          </span>
        </div>
        <p class="mt-4 text-xs font-medium text-slate-400">{{ card.helper }}</p>
      </article>
    </section>

    <div class="grid gap-6 xl:grid-cols-[minmax(0,1.7fr)_minmax(340px,0.8fr)]">
      <section class="min-w-0 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <div class="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 class="text-lg font-black text-slate-900">Xu hướng doanh thu</h2>
            <p class="mt-1 text-sm text-slate-500">{{ periodLabel }}</p>
          </div>
          <div
            v-if="!loading"
            class="flex w-fit items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-bold"
            :class="growth >= 0 ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'"
          >
            <span aria-hidden="true">{{ growth >= 0 ? '↗' : '↘' }}</span>
            {{ Math.abs(growth) }}%
            <span class="font-medium opacity-75">so với kỳ trước</span>
          </div>
        </div>
        <div v-if="loading && !chart.length" class="h-72 animate-pulse rounded-xl bg-slate-50" />
        <RevenueChart v-else :points="chart" />
      </section>

      <section class="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
        <div class="border-b border-slate-100 px-5 py-5 sm:px-6">
          <h2 class="text-lg font-black text-slate-900">Sản phẩm bán chạy</h2>
          <p class="mt-1 text-sm text-slate-500">Xếp hạng theo số lượng bán trong kỳ</p>
        </div>

        <div v-if="loading && !products.length" class="space-y-4 p-5 sm:p-6">
          <div v-for="index in 5" :key="index" class="flex animate-pulse items-center gap-3">
            <div class="h-8 w-8 rounded-lg bg-slate-100" />
            <div class="h-4 flex-1 rounded bg-slate-100" />
            <div class="h-4 w-16 rounded bg-slate-100" />
          </div>
        </div>
        <ol v-else-if="products.length" class="divide-y divide-slate-100 px-5 sm:px-6">
          <li
            v-for="(item, index) in products"
            :key="String(item.product_id || item.id || index)"
            class="grid grid-cols-[auto_minmax(0,1fr)] items-center gap-x-3 gap-y-1 py-4 sm:grid-cols-[auto_minmax(0,1fr)_auto]"
          >
            <span
              class="row-span-2 flex h-8 w-8 items-center justify-center rounded-lg text-xs font-black"
              :class="index < 3 ? 'bg-indigo-50 text-indigo-700' : 'bg-slate-100 text-slate-500'"
            >
              {{ index + 1 }}
            </span>
            <p class="truncate text-sm font-bold text-slate-800">
              {{ item.product_name || 'Sản phẩm chưa đặt tên' }}
            </p>
            <p class="text-xs font-semibold text-slate-500 sm:row-span-2 sm:text-right">
              {{ numberFormatter.format(item.quantity || 0) }} đã bán
            </p>
            <p class="col-start-2 text-xs text-slate-400">
              {{ currencyFormatter.format(Number(item.revenue || 0)) }}
            </p>
          </li>
        </ol>
        <div v-else class="flex flex-col items-center px-6 py-12 text-center">
          <span class="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-slate-100">
            <CubeIcon class="h-6 w-6 text-slate-400" aria-hidden="true" />
          </span>
          <p class="text-sm font-bold text-slate-700">Chưa có dữ liệu sản phẩm</p>
          <p class="mt-1 text-xs leading-5 text-slate-500">
            Dữ liệu sẽ xuất hiện khi có đơn hàng trong kỳ.
          </p>
        </div>
      </section>
    </div>
  </div>
</template>
