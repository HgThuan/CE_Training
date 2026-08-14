<script setup lang="ts">
import { AxiosError } from 'axios'
import { onMounted, reactive, ref, watch } from 'vue'

import { adminCatalogApi } from '@/features/admin/api'
import type { Category } from '@/features/product/types'

import type { Voucher, VoucherPayload, VoucherScope } from '../types'

const props = defineProps<{
  scope: VoucherScope
  voucher?: Voucher | null
  saving?: boolean
}>()
const emit = defineEmits<{
  submit: [payload: VoucherPayload]
  cancel: []
}>()

const fieldErrors = ref<Record<string, string>>({})
const serverError = ref('')
const categories = ref<Category[]>([])

function localDate(value: string): string {
  if (!value) return ''
  const date = new Date(value)
  const offset = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offset).toISOString().slice(0, 16)
}

const form = reactive({
  code: '',
  name: '',
  description: '',
  discount_type: 'percent' as VoucherPayload['discount_type'],
  discount_value: 10,
  max_discount_amount: 50000 as number | null,
  min_order_amount: 0,
  total_usage_limit: null as number | null,
  usage_limit_per_user: 1,
  valid_from: localDate(new Date().toISOString()),
  valid_until: localDate(new Date(Date.now() + 7 * 86400000).toISOString()),
  applicable_category: null as string | null,
  collect_type: 'manual' as VoucherPayload['collect_type'],
  stackable_with: [props.scope === 'platform' ? 'shop' : 'platform'] as VoucherScope[],
  is_active: true,
})

watch(
  () => props.voucher,
  (voucher) => {
    if (!voucher) return
    Object.assign(form, {
      code: voucher.code,
      name: voucher.name,
      description: voucher.description,
      discount_type: voucher.discount_type,
      discount_value: Number(voucher.discount_value),
      max_discount_amount:
        voucher.max_discount_amount === null ? null : Number(voucher.max_discount_amount),
      min_order_amount: Number(voucher.min_order_amount),
      total_usage_limit: voucher.total_usage_limit,
      usage_limit_per_user: voucher.usage_limit_per_user,
      valid_from: localDate(voucher.valid_from),
      valid_until: localDate(voucher.valid_until),
      applicable_category: voucher.applicable_category,
      collect_type: voucher.collect_type,
      stackable_with: voucher.stackable_with,
      is_active: voucher.is_active,
    })
  },
  { immediate: true },
)

function validate(): boolean {
  fieldErrors.value = {}
  if (!form.code.trim()) fieldErrors.value.code = 'Mã voucher là bắt buộc'
  if (!form.name.trim()) fieldErrors.value.name = 'Tên chương trình là bắt buộc'
  if (form.discount_value <= 0) fieldErrors.value.discount_value = 'Giá trị giảm phải lớn hơn 0'
  if (form.discount_type === 'percent' && form.discount_value > 100) {
    fieldErrors.value.discount_value = 'Phần trăm giảm không được vượt quá 100%'
  }
  if (
    form.discount_type === 'percent' &&
    (!form.max_discount_amount || form.max_discount_amount <= 0)
  ) {
    fieldErrors.value.max_discount_amount = 'Voucher phần trăm cần mức giảm tối đa'
  }
  if (new Date(form.valid_from) >= new Date(form.valid_until)) {
    fieldErrors.value.valid_until = 'Thời điểm kết thúc phải sau thời điểm bắt đầu'
  }
  if (!props.voucher && new Date(form.valid_from).getTime() < Date.now() - 60_000) {
    fieldErrors.value.valid_from = 'Thời điểm bắt đầu không được ở trong quá khứ'
  }
  return Object.keys(fieldErrors.value).length === 0
}

function submit(): void {
  serverError.value = ''
  if (!validate()) return
  emit('submit', {
    ...form,
    code: form.code.trim().toUpperCase(),
    name: form.name.trim(),
    max_discount_amount: form.discount_type === 'percent' ? form.max_discount_amount : null,
    valid_from: new Date(form.valid_from).toISOString(),
    valid_until: new Date(form.valid_until).toISOString(),
    applicable_category: props.scope === 'platform' ? form.applicable_category || null : null,
  })
}

function showServerError(error: unknown): void {
  if (!(error instanceof AxiosError)) {
    serverError.value = 'Không thể lưu voucher'
    return
  }
  const payload = error.response?.data as
    { message?: string; errors?: Record<string, string[] | string> } | undefined
  serverError.value = payload?.message ?? 'Không thể lưu voucher'
  if (payload?.errors) {
    for (const [field, messages] of Object.entries(payload.errors)) {
      fieldErrors.value[field] = Array.isArray(messages) ? (messages[0] ?? '') : messages
    }
  }
}

defineExpose({ showServerError })

onMounted(async () => {
  if (props.scope !== 'platform') return
  try {
    categories.value = (await adminCatalogApi.categories()).data.data
  } catch {
    categories.value = []
  }
})
</script>

<template>
  <form class="space-y-4" novalidate @submit.prevent="submit">
    <p v-if="serverError" class="rounded-xl bg-rose-50 px-3 py-2 text-sm font-bold text-rose-700">
      {{ serverError }}
    </p>
    <div class="grid gap-4 sm:grid-cols-2">
      <label class="text-sm font-bold"
        >Mã voucher
        <input
          v-model="form.code"
          class="mt-1 w-full rounded-xl border px-3 py-2 font-mono uppercase"
        />
        <span v-if="fieldErrors.code" class="mt-1 block text-xs text-rose-600">{{
          fieldErrors.code
        }}</span>
      </label>
      <label class="text-sm font-bold"
        >Tên chương trình
        <input v-model="form.name" class="mt-1 w-full rounded-xl border px-3 py-2" />
        <span v-if="fieldErrors.name" class="mt-1 block text-xs text-rose-600">{{
          fieldErrors.name
        }}</span>
      </label>
    </div>
    <label class="block text-sm font-bold"
      >Mô tả
      <textarea
        v-model="form.description"
        class="mt-1 w-full rounded-xl border px-3 py-2"
        rows="2"
      />
    </label>
    <div class="grid gap-4 sm:grid-cols-3">
      <label class="text-sm font-bold"
        >Loại giảm
        <select v-model="form.discount_type" class="mt-1 w-full rounded-xl border px-3 py-2">
          <option value="percent">Phần trăm</option>
          <option value="fixed">Số tiền</option>
          <option value="freeship">Miễn phí vận chuyển</option>
        </select>
      </label>
      <label class="text-sm font-bold"
        >Giá trị
        <input
          v-model.number="form.discount_value"
          type="number"
          min="1"
          :max="form.discount_type === 'percent' ? 100 : undefined"
          class="mt-1 w-full rounded-xl border px-3 py-2"
        />
        <span v-if="fieldErrors.discount_value" class="mt-1 block text-xs text-rose-600">{{
          fieldErrors.discount_value
        }}</span>
      </label>
      <label v-if="form.discount_type === 'percent'" class="text-sm font-bold"
        >Giảm tối đa
        <input
          v-model.number="form.max_discount_amount"
          type="number"
          min="1"
          class="mt-1 w-full rounded-xl border px-3 py-2"
        />
        <span v-if="fieldErrors.max_discount_amount" class="mt-1 block text-xs text-rose-600">{{
          fieldErrors.max_discount_amount
        }}</span>
      </label>
    </div>
    <div class="grid gap-4 sm:grid-cols-2">
      <label class="text-sm font-bold"
        >Cách phát hành
        <select v-model="form.collect_type" class="mt-1 w-full rounded-xl border px-3 py-2">
          <option value="manual">Người dùng bấm Lưu</option>
          <option value="auto">Tự động cấp ở checkout</option>
        </select>
      </label>
      <label class="flex items-center gap-2 self-end pb-2 text-sm font-bold">
        <input
          type="checkbox"
          :checked="form.stackable_with.includes(scope === 'platform' ? 'shop' : 'platform')"
          @change="
            form.stackable_with = ($event.target as HTMLInputElement).checked
              ? [scope === 'platform' ? 'shop' : 'platform']
              : []
          "
        />
        <span>
          Cho dùng đồng thời với voucher {{ scope === 'platform' ? 'shop' : 'sàn' }}
          <span class="block text-xs font-normal text-slate-500"
            >Khách có thể áp dụng cả hai voucher trong cùng một đơn hàng.</span
          >
        </span>
      </label>
    </div>
    <div class="grid gap-4 sm:grid-cols-3">
      <label class="text-sm font-bold"
        >Đơn tối thiểu
        <input
          v-model.number="form.min_order_amount"
          type="number"
          min="0"
          class="mt-1 w-full rounded-xl border px-3 py-2"
        />
      </label>
      <label class="text-sm font-bold"
        >Tổng lượt sử dụng
        <input
          v-model.number="form.total_usage_limit"
          type="number"
          min="1"
          placeholder="Để trống = không giới hạn"
          class="mt-1 w-full rounded-xl border px-3 py-2"
        />
      </label>
      <label class="text-sm font-bold"
        >Lượt/người
        <input
          v-model.number="form.usage_limit_per_user"
          type="number"
          min="1"
          class="mt-1 w-full rounded-xl border px-3 py-2"
        />
      </label>
    </div>
    <label v-if="scope === 'platform'" class="block text-sm font-bold"
      >Danh mục áp dụng
      <select
        v-model="form.applicable_category"
        class="mt-1 w-full rounded-xl border bg-white px-3 py-2"
      >
        <option :value="null">Tất cả danh mục</option>
        <option v-for="category in categories" :key="category.id" :value="category.id">
          {{ category.name }}
        </option>
      </select>
    </label>
    <div class="grid gap-4 sm:grid-cols-2">
      <label class="text-sm font-bold"
        >Bắt đầu
        <input
          v-model="form.valid_from"
          type="datetime-local"
          class="mt-1 w-full rounded-xl border px-3 py-2"
        />
        <span v-if="fieldErrors.valid_from" class="mt-1 block text-xs text-rose-600">{{
          fieldErrors.valid_from
        }}</span>
      </label>
      <label class="text-sm font-bold"
        >Kết thúc
        <input
          v-model="form.valid_until"
          type="datetime-local"
          class="mt-1 w-full rounded-xl border px-3 py-2"
        />
        <span v-if="fieldErrors.valid_until" class="mt-1 block text-xs text-rose-600">{{
          fieldErrors.valid_until
        }}</span>
      </label>
    </div>
    <label class="flex items-center gap-2 text-sm font-bold">
      <input v-model="form.is_active" type="checkbox" /> Đang hoạt động
    </label>
    <div class="flex justify-end gap-2 border-t pt-4">
      <button
        type="button"
        class="rounded-xl px-4 py-2 font-bold text-slate-600 hover:bg-slate-100"
        @click="emit('cancel')"
      >
        Hủy
      </button>
      <button
        type="submit"
        :disabled="saving"
        class="rounded-xl bg-indigo-600 px-5 py-2 font-bold text-white disabled:opacity-50"
      >
        {{ saving ? 'Đang lưu...' : 'Lưu voucher' }}
      </button>
    </div>
  </form>
</template>
