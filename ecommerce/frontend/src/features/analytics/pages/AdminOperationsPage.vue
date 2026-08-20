<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { analyticsApi } from '../api'
import type { AuditEntry, ChatbotMetrics, RankingRow, SiteSetting } from '../types'
import type { PaginationMeta } from '@/shared/types/api'

const tab = ref<'reports' | 'chatbot' | 'audit' | 'settings'>('reports')
const ranking = ref<RankingRow[]>([]),
  rates = ref<Record<string, number>>({}),
  logs = ref<AuditEntry[]>([]),
  settings = ref<SiteSetting[]>([])
const chatbot = ref<ChatbotMetrics>({
  sessions: 0,
  handoffs: 0,
  handoff_rate: 0,
  automated_resolution_rate: 0,
  average_response_ms: 0,
  feedback_count: 0,
  feedback_rate: 0,
  csat: 0,
  resolved_feedback: 0,
  unresolved_feedback: 0,
  variants: [],
})
const message = ref(''),
  error = ref(''),
  loadingLogs = ref(false)
const auditFilters = reactive({ action: '', target_type: '', target_id: '' })
const auditMeta = ref<PaginationMeta>({ page: 1, page_size: 20, total_items: 0, total_pages: 0 })

const actionLabels: Record<string, string> = {
  'settings.update': 'Cập nhật cấu hình',
  'report.export': 'Xuất báo cáo',
  lock_shop: 'Khóa gian hàng',
  unlock_shop: 'Mở khóa gian hàng',
  approve_seller: 'Duyệt seller',
  reject_seller: 'Từ chối seller',
}
const targetLabels: Record<string, string> = {
  site_setting: 'Cấu hình hệ thống',
  report: 'Báo cáo',
  seller: 'Seller',
  shop: 'Gian hàng',
  order: 'Đơn hàng',
  product: 'Sản phẩm',
}

async function loadAudit(page = 1) {
  loadingLogs.value = true
  error.value = ''
  try {
    const response = await analyticsApi.auditLogs({
      ...Object.fromEntries(Object.entries(auditFilters).filter(([, value]) => value)),
      page,
      page_size: auditMeta.value.page_size,
    })
    logs.value = response.data.data
    if (response.data.meta) auditMeta.value = response.data.meta
  } catch {
    error.value = 'Không thể tải audit log. Vui lòng thử lại.'
  } finally {
    loadingLogs.value = false
  }
}
async function load() {
  try {
    const [rankingResponse, ratesResponse, settingsResponse, chatbotResponse] = await Promise.all([
      analyticsApi.ranking('top-sellers', 30),
      analyticsApi.rates(30),
      analyticsApi.settings(),
      analyticsApi.chatbotMetrics(30),
    ])
    ranking.value = rankingResponse.data.data
    rates.value = ratesResponse.data.data
    settings.value = settingsResponse.data.data
    chatbot.value = chatbotResponse.data.data
    await loadAudit()
  } catch {
    error.value = 'Không thể tải dữ liệu vận hành.'
  }
}
async function saveSettings() {
  await analyticsApi.updateSettings(settings.value)
  message.value = 'Đã lưu cấu hình hệ thống.'
}
function editValue(item: SiteSetting, event: Event) {
  const value = (event.target as HTMLInputElement).value
  item.value =
    item.value_type === 'boolean'
      ? value === 'true'
      : item.value_type === 'number'
        ? Number(value)
        : value
}
watch(tab, (value) => {
  if (value === 'audit' && !logs.value.length) void loadAudit()
})
onMounted(load)
</script>

<template>
  <main class="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6">
    <div>
      <h1 class="text-3xl font-black">Báo cáo & vận hành</h1>
      <p class="mt-2 text-slate-600">
        Theo dõi hiệu quả kinh doanh, hoạt động quản trị và cấu hình hệ thống.
      </p>
    </div>
    <p v-if="error" class="rounded-xl bg-rose-50 p-3 text-rose-700">{{ error }}</p>
    <div class="flex gap-2 overflow-x-auto border-b border-slate-200">
      <button
        v-for="item in ['reports', 'chatbot', 'audit', 'settings'] as const"
        :key="item"
        class="border-b-2 px-4 py-3 font-bold whitespace-nowrap"
        :class="
          tab === item ? 'border-indigo-600 text-indigo-700' : 'border-transparent text-slate-500'
        "
        @click="tab = item"
      >
        {{
          {
            reports: 'Báo cáo',
            chatbot: 'Hiệu quả chatbot',
            audit: 'Audit log',
            settings: 'Cấu hình',
          }[item]
        }}
      </button>
    </div>
    <section v-if="tab === 'reports'" class="space-y-5">
      <div class="grid gap-4 sm:grid-cols-3">
        <article
          v-for="metric in [
            { label: 'Tổng đơn', value: rates.total_orders },
            { label: 'Tỷ lệ hủy', value: `${rates.cancel_rate || 0}%` },
            { label: 'Tỷ lệ trả', value: `${rates.return_rate || 0}%` },
          ]"
          :key="metric.label"
          class="rounded-2xl bg-white p-5 ring-1 ring-slate-200"
        >
          <p class="text-sm text-slate-500">{{ metric.label }}</p>
          <p class="text-2xl font-black">{{ metric.value }}</p>
        </article>
      </div>
      <div class="rounded-2xl bg-white p-6 ring-1 ring-slate-200">
        <h2 class="mb-3 text-lg font-black">Top seller theo doanh thu</h2>
        <div
          v-for="(row, index) in ranking"
          :key="String(row.id)"
          class="flex justify-between border-b py-3"
        >
          <span>#{{ index + 1 }} · {{ row.name }}</span
          ><b>{{ Number(row.revenue).toLocaleString('vi-VN') }} ₫</b>
        </div>
      </div>
    </section>
    <section v-else-if="tab === 'chatbot'" class="space-y-5">
      <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <article
          v-for="metric in [
            { label: 'Phiên hội thoại', value: chatbot.sessions },
            { label: 'Tự động giải quyết', value: `${chatbot.automated_resolution_rate}%` },
            { label: 'Chuyển CSKH', value: `${chatbot.handoff_rate}%` },
            { label: 'CSAT', value: `${chatbot.csat}/5` },
            { label: 'Phản hồi', value: `${chatbot.feedback_rate}%` },
            { label: 'Phản hồi tích cực', value: chatbot.resolved_feedback },
            { label: 'Cần cải thiện', value: chatbot.unresolved_feedback },
            { label: 'Phản hồi trung bình', value: `${chatbot.average_response_ms} ms` },
          ]"
          :key="metric.label"
          class="rounded-2xl bg-white p-5 ring-1 ring-slate-200"
        >
          <p class="text-sm text-slate-500">{{ metric.label }}</p>
          <p class="mt-1 text-2xl font-black">{{ metric.value }}</p>
        </article>
      </div>
      <div class="overflow-x-auto rounded-2xl bg-white p-6 ring-1 ring-slate-200">
        <h2 class="mb-4 text-lg font-black">A/B test trải nghiệm hội thoại</h2>
        <table class="w-full min-w-[620px] text-left text-sm">
          <thead class="border-b text-slate-500">
            <tr>
              <th class="py-3">Biến thể</th>
              <th>Phiên</th>
              <th>CSAT</th>
              <th>Tỷ lệ handoff</th>
              <th>Số phản hồi</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="variant in chatbot.variants"
              :key="variant.experiment_variant"
              class="border-b"
            >
              <td class="py-3 font-bold">{{ variant.experiment_variant }}</td>
              <td>{{ variant.sessions }}</td>
              <td>{{ variant.csat }}/5</td>
              <td>{{ variant.handoff_rate }}%</td>
              <td>{{ variant.feedback_count }}</td>
            </tr>
            <tr v-if="!chatbot.variants.length">
              <td colspan="5" class="py-8 text-center text-slate-500">
                Chưa có dữ liệu thử nghiệm.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
    <section v-else-if="tab === 'audit'" class="space-y-4">
      <form
        class="grid gap-3 rounded-2xl bg-white p-4 ring-1 ring-slate-200 md:grid-cols-4"
        @submit.prevent="loadAudit(1)"
      >
        <input
          v-model.trim="auditFilters.action"
          class="rounded-xl border p-3"
          placeholder="Hành động, VD: report.export"
        /><input
          v-model.trim="auditFilters.target_type"
          class="rounded-xl border p-3"
          placeholder="Loại đối tượng"
        /><input
          v-model.trim="auditFilters.target_id"
          class="rounded-xl border p-3"
          placeholder="Mã đối tượng"
        /><button class="rounded-xl bg-slate-950 font-bold text-white">Tìm kiếm</button>
      </form>
      <div class="overflow-x-auto rounded-2xl bg-white ring-1 ring-slate-200">
        <table class="w-full min-w-[850px] text-left text-sm">
          <thead class="bg-slate-50">
            <tr>
              <th class="p-3">Thời gian</th>
              <th>Người thực hiện</th>
              <th>Hoạt động quản trị</th>
              <th>Đối tượng bị tác động</th>
              <th>Request ID</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loadingLogs">
              <td colspan="5" class="p-8 text-center">Đang tải…</td>
            </tr>
            <tr v-for="row in logs" :key="row.id" class="border-t">
              <td class="p-3">{{ new Date(row.created_at).toLocaleString('vi-VN') }}</td>
              <td>{{ row.actor }}</td>
              <td class="font-semibold">{{ actionLabels[row.action] ?? row.action }}</td>
              <td>{{ targetLabels[row.target_type] ?? row.target_type }} · {{ row.target_id }}</td>
              <td class="font-mono text-xs">{{ row.request_id || '—' }}</td>
            </tr>
            <tr v-if="!loadingLogs && !logs.length">
              <td colspan="5" class="p-8 text-center text-slate-500">Không có bản ghi phù hợp.</td>
            </tr>
          </tbody>
        </table>
      </div>
      <nav v-if="auditMeta.total_pages > 1" class="flex items-center justify-between text-sm">
        <span>{{ auditMeta.total_items }} bản ghi</span>
        <div class="flex gap-2">
          <button
            class="rounded-xl border px-4 py-2 disabled:opacity-40"
            :disabled="auditMeta.page <= 1"
            @click="loadAudit(auditMeta.page - 1)"
          >
            Trang trước</button
          ><button
            class="rounded-xl border px-4 py-2 disabled:opacity-40"
            :disabled="auditMeta.page >= auditMeta.total_pages"
            @click="loadAudit(auditMeta.page + 1)"
          >
            Trang sau
          </button>
        </div>
      </nav>
    </section>
    <section v-else class="space-y-4 rounded-2xl bg-white p-6 ring-1 ring-slate-200">
      <p v-if="message" class="rounded-xl bg-emerald-50 p-3 text-emerald-700">{{ message }}</p>
      <div
        v-for="item in settings"
        :key="item.key"
        class="grid gap-2 border-b pb-4 md:grid-cols-[1fr_2fr]"
      >
        <div>
          <label class="font-bold">{{ item.key }}</label>
          <p class="text-sm text-slate-500">{{ item.description }}</p>
        </div>
        <select
          v-if="item.value_type === 'boolean'"
          :value="String(item.value)"
          class="rounded-xl border p-2"
          @change="editValue(item, $event)"
        >
          <option value="true">Bật</option>
          <option value="false">Tắt</option></select
        ><input
          v-else
          :value="String(item.value ?? '')"
          class="rounded-xl border p-2"
          @input="editValue(item, $event)"
        />
      </div>
      <button class="rounded-xl bg-indigo-600 px-5 py-3 font-bold text-white" @click="saveSettings">
        Lưu cấu hình
      </button>
      <p v-if="!settings.length" class="text-slate-500">Chưa có cấu hình hệ thống.</p>
    </section>
  </main>
</template>
