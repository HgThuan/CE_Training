<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { analyticsApi } from '../api'
import type { AuditEntry, RankingRow, SiteSetting } from '../types'

const tab = ref<'reports' | 'audit' | 'settings'>('reports')
const ranking = ref<RankingRow[]>([])
const rates = ref<Record<string, number>>({})
const logs = ref<AuditEntry[]>([])
const settings = ref<SiteSetting[]>([])
const message = ref('')

async function load() {
  const [rankingResponse, ratesResponse, logsResponse, settingsResponse] = await Promise.all([
    analyticsApi.ranking('top-sellers', 30), analyticsApi.rates(30), analyticsApi.auditLogs(), analyticsApi.settings(),
  ])
  ranking.value = rankingResponse.data.data
  rates.value = ratesResponse.data.data
  logs.value = logsResponse.data.data
  settings.value = settingsResponse.data.data
}

async function saveSettings() {
  await analyticsApi.updateSettings(settings.value)
  message.value = 'Đã lưu cấu hình hệ thống.'
}

function editValue(item: SiteSetting, event: Event) {
  const value = (event.target as HTMLInputElement).value
  if (item.value_type === 'boolean') item.value = value === 'true'
  else if (item.value_type === 'number') item.value = Number(value)
  else item.value = value
}

onMounted(load)
</script>

<template>
  <main class="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6">
    <div><p class="text-sm font-bold uppercase tracking-widest text-indigo-600">Administration</p><h1 class="text-3xl font-black">Báo cáo & vận hành</h1></div>
    <div class="flex gap-2 border-b border-slate-200"><button v-for="item in ['reports', 'audit', 'settings'] as const" :key="item" class="border-b-2 px-4 py-3 font-bold" :class="tab === item ? 'border-indigo-600 text-indigo-700' : 'border-transparent text-slate-500'" @click="tab = item">{{ { reports: 'Báo cáo', audit: 'Audit log', settings: 'Cấu hình' }[item] }}</button></div>
    <section v-if="tab === 'reports'" class="space-y-5">
      <div class="grid gap-4 sm:grid-cols-3"><article v-for="metric in [{ label: 'Tổng đơn', value: rates.total_orders }, { label: 'Tỷ lệ hủy', value: `${rates.cancel_rate || 0}%` }, { label: 'Tỷ lệ trả', value: `${rates.return_rate || 0}%` }]" :key="metric.label" class="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200"><p class="text-sm text-slate-500">{{ metric.label }}</p><p class="text-2xl font-black">{{ metric.value }}</p></article></div>
      <div class="rounded-2xl bg-white p-6 ring-1 ring-slate-200"><h2 class="mb-3 text-lg font-black">Top seller theo doanh thu</h2><div v-for="(row, index) in ranking" :key="String(row.id)" class="flex justify-between border-b py-3"><span>#{{ index + 1 }} · {{ row.name }}</span><b>{{ Number(row.revenue).toLocaleString('vi-VN') }} ₫</b></div></div>
    </section>
    <section v-else-if="tab === 'audit'" class="overflow-x-auto rounded-2xl bg-white ring-1 ring-slate-200"><table class="w-full text-left text-sm"><thead class="bg-slate-50"><tr><th class="p-3">Thời gian</th><th class="p-3">Người thực hiện</th><th class="p-3">Hành động</th><th class="p-3">Đối tượng</th><th class="p-3">Request ID</th></tr></thead><tbody><tr v-for="row in logs" :key="row.id" class="border-t"><td class="p-3">{{ new Date(row.created_at).toLocaleString('vi-VN') }}</td><td class="p-3">{{ row.actor }}</td><td class="p-3 font-semibold">{{ row.action }}</td><td class="p-3">{{ row.target_type }}:{{ row.target_id }}</td><td class="p-3 font-mono text-xs">{{ row.request_id || '—' }}</td></tr></tbody></table></section>
    <section v-else class="space-y-4 rounded-2xl bg-white p-6 ring-1 ring-slate-200"><p v-if="message" class="rounded-xl bg-emerald-50 p-3 text-emerald-700">{{ message }}</p><div v-for="item in settings" :key="item.key" class="grid gap-2 border-b pb-4 md:grid-cols-[1fr_2fr]"><div><label class="font-bold">{{ item.key }}</label><p class="text-sm text-slate-500">{{ item.description }}</p></div><select v-if="item.value_type === 'boolean'" :value="String(item.value)" class="rounded-xl border p-2" @change="editValue(item, $event)"><option value="true">Bật</option><option value="false">Tắt</option></select><input v-else :value="String(item.value ?? '')" class="rounded-xl border p-2" @input="editValue(item, $event)" /></div><button class="rounded-xl bg-indigo-600 px-5 py-3 font-bold text-white" @click="saveSettings">Lưu cấu hình</button><p v-if="!settings.length" class="text-slate-500">Chưa có cấu hình. Có thể khởi tạo qua API PUT settings.</p></section>
  </main>
</template>
