<script setup lang="ts">
import {
  ArrowPathIcon,
  ClipboardDocumentCheckIcon,
  DocumentArrowDownIcon,
  ExclamationTriangleIcon,
  MagnifyingGlassIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'
import { computed, onMounted, ref } from 'vue'

import { orderApi } from '@/features/order/api'
import type { ShopOrder } from '@/features/order/types'
import { formatCurrency } from '@/shared/lib/formatters'

const orders = ref<ShopOrder[]>([])
const loading = ref(true)
const acting = ref(false)
const error = ref('')
const search = ref('')
const status = ref('')
const actionTarget = ref<ShopOrder | null>(null)
const pendingAction = ref('')
const cancellationReason = ref('')

const statusOptions = [
  { value: '', label: 'Mọi trạng thái' },
  { value: 'PENDING_CONFIRMATION', label: 'Chờ xác nhận' },
  { value: 'CONFIRMED', label: 'Đã xác nhận' },
  { value: 'PACKING', label: 'Đang đóng gói' },
  { value: 'SHIPPING', label: 'Đang giao' },
  { value: 'COMPLETED', label: 'Hoàn thành' },
  { value: 'CANCELLED', label: 'Đã hủy' },
]

const actionMap: Record<string, string[]> = {
  PENDING_CONFIRMATION: ['confirm', 'cancel'],
  CONFIRMED: ['pack', 'cancel'],
  PACKING: ['ship', 'cancel'],
  SHIPPING: ['complete'],
}

const actionLabels: Record<string, string> = {
  confirm: 'Xác nhận đơn',
  pack: 'Bắt đầu đóng gói',
  ship: 'Bàn giao vận chuyển',
  complete: 'Xác nhận hoàn thành',
  cancel: 'Hủy đơn',
}

const statusLabels = Object.fromEntries(statusOptions.map((item) => [item.value, item.label]))

const filteredOrders = computed(() => {
  const keyword = search.value.trim().toLocaleLowerCase('vi-VN')
  return orders.value.filter((order) => {
    const matchesStatus = !status.value || order.fulfillment_status === status.value
    const matchesSearch =
      !keyword ||
      [order.shop_order_code, order.order_code, order.customer_email]
        .filter(Boolean)
        .some((value) => String(value).toLocaleLowerCase('vi-VN').includes(keyword))
    return matchesStatus && matchesSearch
  })
})

function statusClass(value: string): string {
  if (['COMPLETED', 'DELIVERED'].includes(value)) return 'bg-emerald-50 text-emerald-700'
  if (value === 'CANCELLED') return 'bg-rose-50 text-rose-700'
  if (value === 'SHIPPING') return 'bg-sky-50 text-sky-700'
  return 'bg-amber-50 text-amber-800'
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    orders.value = (await orderApi.sellerOrders()).data.data
  } catch {
    error.value = 'Không thể tải đơn của gian hàng. Vui lòng thử lại.'
  } finally {
    loading.value = false
  }
}

function requestAction(item: ShopOrder, action: string): void {
  actionTarget.value = item
  pendingAction.value = action
  cancellationReason.value = ''
}

function closeAction(): void {
  if (acting.value) return
  actionTarget.value = null
  pendingAction.value = ''
  cancellationReason.value = ''
}

async function confirmAction(): Promise<void> {
  if (!actionTarget.value || !pendingAction.value) return
  if (pendingAction.value === 'cancel' && !cancellationReason.value.trim()) return
  acting.value = true
  error.value = ''
  try {
    await orderApi.sellerAction(
      actionTarget.value.id,
      pendingAction.value,
      cancellationReason.value.trim(),
    )
    actionTarget.value = null
    pendingAction.value = ''
    cancellationReason.value = ''
    await load()
  } catch {
    error.value = 'Chưa thể cập nhật trạng thái đơn. Dữ liệu hiện tại vẫn được giữ nguyên.'
  } finally {
    acting.value = false
  }
}

async function printPackingSlip(item: ShopOrder): Promise<void> {
  const popup = window.open('', '_blank')
  try {
    const response = await orderApi.packingSlip(item.id)
    const url = URL.createObjectURL(new Blob([response.data], { type: 'text/html;charset=utf-8' }))
    if (popup) popup.location.href = url
    else window.open(url, '_blank')
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000)
  } catch {
    popup?.close()
    error.value = 'Không thể tải phiếu đóng gói.'
  }
}

onMounted(load)
</script>

<template>
  <main class="app-page" :aria-busy="loading">
    <header class="app-page-header">
      <div>
        <p class="app-page-eyebrow">Bán hàng · Thực hiện đơn</p>
        <h1 class="app-page-title">Xử lý đơn hàng</h1>
        <p class="app-page-description">
          Mỗi đơn chỉ thuộc gian hàng đang đăng nhập. Hãy cập nhật đúng từng bước để khách nhận
          thông báo kịp thời.
        </p>
      </div>
      <button class="workspace-page-action" type="button" :disabled="loading" @click="load">
        <ArrowPathIcon class="h-5 w-5" :class="{ 'animate-spin': loading }" aria-hidden="true" />
        Làm mới
      </button>
    </header>

    <div v-if="error" class="workspace-alert workspace-alert--error" role="alert">
      <ExclamationTriangleIcon class="h-5 w-5 shrink-0" aria-hidden="true" />
      <span>{{ error }}</span>
      <button type="button" @click="load">Thử lại</button>
    </div>

    <section class="workspace-filter-bar" aria-label="Bộ lọc đơn hàng">
      <label class="workspace-search-field">
        <span class="sr-only">Tìm theo mã đơn hoặc email khách</span>
        <MagnifyingGlassIcon class="h-5 w-5" aria-hidden="true" />
        <input v-model="search" type="search" placeholder="Tìm mã đơn hoặc email khách…" />
      </label>
      <label>
        <span class="sr-only">Lọc trạng thái</span>
        <select v-model="status">
          <option v-for="item in statusOptions" :key="item.value || 'all'" :value="item.value">
            {{ item.label }}
          </option>
        </select>
      </label>
      <p>{{ filteredOrders.length }} / {{ orders.length }} đơn</p>
    </section>

    <section v-if="loading" class="app-card mt-5 space-y-3 p-5" aria-label="Đang tải đơn">
      <div v-for="index in 5" :key="index" class="h-14 animate-pulse rounded-xl bg-slate-100" />
    </section>

    <section v-else-if="!filteredOrders.length" class="workspace-empty-state">
      <ClipboardDocumentCheckIcon class="h-10 w-10" aria-hidden="true" />
      <h2>Không có đơn phù hợp</h2>
      <p>Thử thay đổi từ khóa hoặc bộ lọc trạng thái.</p>
    </section>

    <section v-else class="workspace-table-card">
      <div class="overflow-x-auto">
        <table class="workspace-table min-w-[980px]">
          <thead>
            <tr>
              <th>Đơn hàng</th>
              <th>Khách mua</th>
              <th>Trạng thái</th>
              <th>Sản phẩm</th>
              <th class="text-right">Tổng tiền</th>
              <th class="text-right">Thao tác</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in filteredOrders" :key="item.id">
              <td>
                <strong class="font-mono text-slate-950">{{ item.shop_order_code }}</strong>
                <span class="mt-1 block text-xs text-slate-500">{{ item.order_code || '—' }}</span>
              </td>
              <td>{{ item.customer_email || 'Khách hàng' }}</td>
              <td>
                <span class="app-status" :class="statusClass(item.fulfillment_status)">
                  {{ statusLabels[item.fulfillment_status] || item.fulfillment_status }}
                </span>
              </td>
              <td>
                <strong>{{ item.items.length }} dòng sản phẩm</strong>
                <span class="mt-1 block text-xs text-slate-500">
                  {{ item.items.reduce((total, product) => total + product.quantity, 0) }} sản phẩm
                </span>
              </td>
              <td class="text-right font-extrabold text-slate-950">
                {{ formatCurrency(item.total_amount) }}
              </td>
              <td>
                <div class="flex justify-end gap-2">
                  <button
                    v-for="action in actionMap[item.fulfillment_status] || []"
                    :key="action"
                    type="button"
                    class="workspace-table-action"
                    :class="{ 'workspace-table-action--danger': action === 'cancel' }"
                    @click="requestAction(item, action)"
                  >
                    {{ actionLabels[action] }}
                  </button>
                  <button
                    type="button"
                    class="workspace-table-icon-action"
                    aria-label="In phiếu đóng gói"
                    title="In phiếu đóng gói"
                    @click="printPackingSlip(item)"
                  >
                    <DocumentArrowDownIcon class="h-5 w-5" aria-hidden="true" />
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <div v-if="actionTarget" class="app-modal" role="presentation" @click.self="closeAction">
      <section
        class="app-modal__panel"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="'seller-order-action-title'"
      >
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="app-page-eyebrow">Cập nhật trạng thái</p>
            <h2 id="seller-order-action-title" class="mt-1 text-xl font-black text-slate-950">
              {{ actionLabels[pendingAction] }}
            </h2>
            <p class="mt-2 text-sm text-slate-500">Đơn {{ actionTarget.shop_order_code }}</p>
          </div>
          <button type="button" class="workspace-icon-button" aria-label="Đóng" @click="closeAction">
            <XMarkIcon class="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        <p class="mt-5 rounded-xl bg-slate-50 p-4 text-sm leading-6 text-slate-600">
          {{
            pendingAction === 'cancel'
              ? 'Khách hàng sẽ nhìn thấy lý do hủy. Hãy mô tả ngắn gọn, chính xác và hữu ích.'
              : 'Hệ thống sẽ thông báo trạng thái mới đến khách hàng sau khi xác nhận.'
          }}
        </p>

        <label v-if="pendingAction === 'cancel'" class="mt-5 block text-sm font-bold text-slate-700">
          Lý do hủy <span class="text-rose-600">*</span>
          <textarea
            v-model.trim="cancellationReason"
            class="mt-2 min-h-28 w-full rounded-xl border border-slate-300 p-3"
            maxlength="500"
            placeholder="Ví dụ: Sản phẩm tạm hết hàng và chưa có lịch nhập mới…"
          />
        </label>

        <div class="mt-6 flex justify-end gap-3">
          <button type="button" class="workspace-page-action" :disabled="acting" @click="closeAction">
            Quay lại
          </button>
          <button
            type="button"
            class="workspace-primary-action"
            :class="{ 'workspace-primary-action--danger': pendingAction === 'cancel' }"
            :disabled="acting || (pendingAction === 'cancel' && !cancellationReason.trim())"
            @click="confirmAction"
          >
            {{ acting ? 'Đang cập nhật…' : `Xác nhận ${actionLabels[pendingAction].toLowerCase()}` }}
          </button>
        </div>
      </section>
    </div>
  </main>
</template>
