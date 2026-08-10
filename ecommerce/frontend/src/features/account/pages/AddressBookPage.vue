<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import FormMessage from '@/features/auth/components/FormMessage.vue'
import { getErrorMessage } from '@/features/auth/errors'
import { showConfirm } from '@/shared/lib/dialog'

import { accountApi } from '../api'
import type { Address, AddressPayload } from '../types'

const locationSuggestions = [
  {
    province: 'Hà Nội',
    districts: [
      { district: 'Ba Đình', wards: ['Điện Biên', 'Đội Cấn', 'Ngọc Hà'] },
      { district: 'Cầu Giấy', wards: ['Dịch Vọng', 'Nghĩa Đô', 'Yên Hòa'] },
      { district: 'Đống Đa', wards: ['Cát Linh', 'Láng Hạ', 'Ô Chợ Dừa'] },
    ],
  },
  {
    province: 'TP. Hồ Chí Minh',
    districts: [
      { district: 'Quận 1', wards: ['Bến Nghé', 'Bến Thành', 'Đa Kao'] },
      { district: 'Quận 3', wards: ['Phường 4', 'Phường 5', 'Võ Thị Sáu'] },
      { district: 'Thành phố Thủ Đức', wards: ['An Khánh', 'Hiệp Bình Chánh', 'Thảo Điền'] },
    ],
  },
  {
    province: 'Đà Nẵng',
    districts: [
      { district: 'Hải Châu', wards: ['Hải Châu I', 'Hòa Cường Bắc', 'Thạch Thang'] },
      { district: 'Sơn Trà', wards: ['An Hải Bắc', 'Mân Thái', 'Phước Mỹ'] },
    ],
  },
  {
    province: 'Hải Phòng',
    districts: [
      { district: 'Hồng Bàng', wards: ['Hoàng Văn Thụ', 'Hùng Vương', 'Sở Dầu'] },
      { district: 'Lê Chân', wards: ['An Biên', 'Dư Hàng', 'Kênh Dương'] },
    ],
  },
  {
    province: 'Cần Thơ',
    districts: [
      { district: 'Ninh Kiều', wards: ['An Cư', 'Cái Khế', 'Tân An'] },
      { district: 'Bình Thủy', wards: ['Bình Thủy', 'Long Hòa', 'Trà An'] },
    ],
  },
]

const emptyForm = (): AddressPayload => ({
  recipient_name: '',
  phone: '',
  province: '',
  district: '',
  ward: '',
  detail_address: '',
  is_default: false,
})

const addresses = ref<Address[]>([])
const form = reactive<AddressPayload>(emptyForm())
const editingId = ref<number | null>(null)
const loading = ref(true)
const saving = ref(false)
const message = ref('')
const errorMessage = ref('')

const selectedProvince = computed(() =>
  locationSuggestions.find((item) => item.province === form.province),
)
const districtSuggestions = computed(
  () => selectedProvince.value?.districts.map((item) => item.district) ?? [],
)
const wardSuggestions = computed(
  () =>
    selectedProvince.value?.districts.find((item) => item.district === form.district)?.wards ?? [],
)

function resetForm(): void {
  Object.assign(form, emptyForm())
  editingId.value = null
}

function changeProvince(): void {
  form.district = ''
  form.ward = ''
}

function changeDistrict(): void {
  form.ward = ''
}

async function loadAddresses(): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await accountApi.listAddresses()
    addresses.value = response.data.data
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
}

async function saveAddress(): Promise<void> {
  saving.value = true
  message.value = ''
  errorMessage.value = ''
  try {
    const response = editingId.value
      ? await accountApi.updateAddress(editingId.value, { ...form })
      : await accountApi.createAddress({ ...form })
    message.value = response.data.message
    resetForm()
    await loadAddresses()
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    saving.value = false
  }
}

function editAddress(address: Address): void {
  editingId.value = address.id
  Object.assign(form, {
    recipient_name: address.recipient_name,
    phone: address.phone,
    province: address.province,
    district: address.district,
    ward: address.ward,
    detail_address: address.detail_address,
    is_default: address.is_default,
  })
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

async function removeAddress(address: Address): Promise<void> {
  if (!(await showConfirm(`Xóa địa chỉ của ${address.recipient_name}?`, { tone: 'danger' }))) return
  errorMessage.value = ''
  try {
    const response = await accountApi.deleteAddress(address.id)
    message.value = response.data.message
    if (editingId.value === address.id) resetForm()
    await loadAddresses()
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
}

async function setDefault(address: Address): Promise<void> {
  errorMessage.value = ''
  try {
    const response = await accountApi.setDefaultAddress(address.id)
    message.value = response.data.message
    await loadAddresses()
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  }
}

onMounted(loadAddresses)
</script>

<template>
  <main class="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-12">
    <header class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <p class="text-sm font-bold uppercase tracking-[0.2em] text-indigo-600">CUS-06</p>
        <h1 class="mt-2 text-3xl font-bold text-gray-950">Sổ địa chỉ</h1>
        <p class="mt-2 text-gray-600">Quản lý địa chỉ nhận hàng dùng trong bước checkout.</p>
      </div>
      <RouterLink
        class="rounded-xl border border-gray-300 px-4 py-2 font-semibold"
        to="/account/profile"
      >
        Hồ sơ cá nhân
      </RouterLink>
    </header>

    <FormMessage v-if="message" class="mt-6" :message="message" variant="success" />
    <FormMessage v-if="errorMessage" class="mt-6" :message="errorMessage" />

    <div class="mt-8 grid gap-8 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
      <form
        class="space-y-4 rounded-2xl bg-white p-5 ring-1 ring-gray-200 sm:p-6"
        @submit.prevent="saveAddress"
      >
        <div class="flex items-center justify-between gap-3">
          <h2 class="text-xl font-bold">{{ editingId ? 'Sửa địa chỉ' : 'Thêm địa chỉ' }}</h2>
          <button
            v-if="editingId"
            class="text-sm font-semibold text-gray-600"
            type="button"
            @click="resetForm"
          >
            Hủy sửa
          </button>
        </div>
        <label class="block text-sm font-medium">
          Người nhận
          <input
            v-model.trim="form.recipient_name"
            class="mt-2 w-full rounded-xl border px-3 py-2.5"
            maxlength="255"
            required
          />
        </label>
        <label class="block text-sm font-medium">
          Số điện thoại
          <input
            v-model.trim="form.phone"
            class="mt-2 w-full rounded-xl border px-3 py-2.5"
            inputmode="tel"
            pattern="\+?[0-9]{9,15}"
            required
          />
        </label>
        <div class="grid gap-4 sm:grid-cols-3">
          <label class="block text-sm font-medium">
            Tỉnh/thành
            <select
              v-model="form.province"
              class="mt-2 w-full rounded-xl border px-3 py-2.5"
              required
              @change="changeProvince"
            >
              <option value="" disabled>Chọn tỉnh/thành</option>
              <option
                v-for="item in locationSuggestions"
                :key="item.province"
                :value="item.province"
              >
                {{ item.province }}
              </option>
            </select>
          </label>
          <label class="block text-sm font-medium">
            Quận/huyện
            <select
              v-model="form.district"
              class="mt-2 w-full rounded-xl border px-3 py-2.5"
              :disabled="!form.province"
              required
              @change="changeDistrict"
            >
              <option value="" disabled>Chọn quận/huyện</option>
              <option v-for="district in districtSuggestions" :key="district" :value="district">
                {{ district }}
              </option>
            </select>
          </label>
          <label class="block text-sm font-medium">
            Phường/xã
            <select
              v-model="form.ward"
              class="mt-2 w-full rounded-xl border px-3 py-2.5"
              :disabled="!form.district"
              required
            >
              <option value="" disabled>Chọn phường/xã</option>
              <option v-for="ward in wardSuggestions" :key="ward" :value="ward">
                {{ ward }}
              </option>
            </select>
          </label>
        </div>
        <label class="block text-sm font-medium">
          Địa chỉ chi tiết
          <textarea
            v-model.trim="form.detail_address"
            class="mt-2 min-h-24 w-full rounded-xl border px-3 py-2.5"
            maxlength="500"
            required
          />
        </label>
        <label class="flex items-center gap-3 text-sm font-medium">
          <input v-model="form.is_default" class="size-4" type="checkbox" />
          Dùng làm địa chỉ mặc định
        </label>
        <button
          class="w-full rounded-xl bg-indigo-600 px-4 py-3 font-semibold text-white disabled:opacity-60"
          :disabled="saving"
          type="submit"
        >
          {{ saving ? 'Đang lưu…' : editingId ? 'Lưu thay đổi' : 'Thêm địa chỉ' }}
        </button>
      </form>

      <section>
        <h2 class="text-xl font-bold">Địa chỉ đã lưu</h2>
        <p v-if="loading" class="mt-4 text-gray-600">Đang tải địa chỉ…</p>
        <p
          v-else-if="addresses.length === 0"
          class="mt-4 rounded-2xl border border-dashed border-gray-300 p-8 text-center text-gray-600"
        >
          Bạn chưa lưu địa chỉ nào.
        </p>
        <div v-else class="mt-4 space-y-4">
          <article
            v-for="address in addresses"
            :key="address.id"
            class="rounded-2xl bg-white p-5 ring-1 ring-gray-200"
          >
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div class="flex flex-wrap items-center gap-2">
                  <h3 class="font-bold text-gray-950">{{ address.recipient_name }}</h3>
                  <span
                    v-if="address.is_default"
                    class="rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-bold text-indigo-700"
                    >Mặc định</span
                  >
                </div>
                <p class="mt-1 text-sm text-gray-600">{{ address.phone }}</p>
                <p class="mt-3 leading-6 text-gray-800">
                  {{ address.detail_address }}, {{ address.ward }}, {{ address.district }},
                  {{ address.province }}
                </p>
              </div>
              <div class="flex flex-wrap gap-2 text-sm font-semibold">
                <button
                  v-if="!address.is_default"
                  class="rounded-lg border px-3 py-2"
                  type="button"
                  @click="setDefault(address)"
                >
                  Đặt mặc định
                </button>
                <button
                  class="rounded-lg border px-3 py-2"
                  type="button"
                  @click="editAddress(address)"
                >
                  Sửa
                </button>
                <button
                  class="rounded-lg border border-red-200 px-3 py-2 text-red-700"
                  type="button"
                  @click="removeAddress(address)"
                >
                  Xóa
                </button>
              </div>
            </div>
          </article>
        </div>
      </section>
    </div>
  </main>
</template>
