<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { accountApi } from '@/features/account/api'
import type { Address, AddressPayload } from '@/features/account/types'
import { useCartStore } from '@/features/cart/store'
import { orderApi } from '@/features/order/api'
import type { CheckoutPreview } from '@/features/order/types'
import { promotionApi } from '@/features/promotion/api'
import type { CheckoutVoucher } from '@/features/promotion/types'
import { formatCurrency } from '@/shared/lib/formatters'

const router = useRouter()
const cartStore = useCartStore()
const addresses = ref<Address[]>([])
const addressId = ref<number | null>(null)
const editingAddress = ref(false)
const addressDraft = ref<AddressPayload | null>(null)
const paymentMethod = ref<'COD' | 'VNPAY'>('COD')
const platformCoupon = ref('')
const shopCouponCodes = reactive<Record<string, string>>({})
const shopNotes = reactive<Record<string, string>>({})
const shippingMethods = reactive<Record<string, string>>({})
const vouchers = ref<CheckoutVoucher[]>([])
const preview = ref<CheckoutPreview | null>(null)
const loading = ref(false)
const savingAddress = ref(false)
const submitting = ref(false)
const initialized = ref(false)
const error = ref('')

const selectedItemIds = computed(() => cartStore.selectedValidItems.map((item) => item.id))
const selectedAddress = computed(
  () => addresses.value.find((address) => address.id === addressId.value) ?? null,
)
const platformVouchers = computed(() =>
  vouchers.value.filter((voucher) => voucher.is_eligible && voucher.campaign.scope === 'platform'),
)
const canSubmit = computed(() =>
  Boolean(addressId.value && preview.value && selectedItemIds.value.length && !submitting.value),
)

function shopVouchers(shopId: number): CheckoutVoucher[] {
  return vouchers.value.filter(
    (voucher) =>
      voucher.is_eligible &&
      voucher.campaign.scope === 'shop' &&
      Number(voucher.campaign.shop) === shopId,
  )
}

function checkoutPayload() {
  return {
    address_id: addressId.value,
    payment_method: paymentMethod.value,
    cart_item_ids: selectedItemIds.value,
    coupons: {
      platform: platformCoupon.value || undefined,
      shops: Object.fromEntries(Object.entries(shopCouponCodes).filter(([, code]) => code)),
    },
    shop_notes: { ...shopNotes },
    shipping_methods: Object.fromEntries(
      Object.entries(shippingMethods).map(([shopId, code]) => [
        shopId,
        { code, name: 'Giao hàng tiêu chuẩn (phí cố định)' },
      ]),
    ),
  }
}

async function loadPreview(): Promise<void> {
  if (!selectedItemIds.value.length) return
  loading.value = true
  error.value = ''
  try {
    preview.value = (await orderApi.preview(checkoutPayload())).data.data
    for (const shop of preview.value.shops) {
      shippingMethods[String(shop.shop_id)] ??= 'STANDARD'
      shopNotes[String(shop.shop_id)] ??= ''
      shopCouponCodes[String(shop.shop_id)] ??= ''
    }
  } catch (cause) {
    preview.value = null
    error.value = cause instanceof Error ? cause.message : 'Không thể tính checkout.'
  } finally {
    loading.value = false
  }
}

function editSelectedAddress(): void {
  if (!selectedAddress.value) return
  const { recipient_name, phone, province, district, ward, detail_address, is_default } =
    selectedAddress.value
  addressDraft.value = {
    recipient_name,
    phone,
    province,
    district,
    ward,
    detail_address,
    is_default,
  }
  editingAddress.value = true
}

async function saveAddress(): Promise<void> {
  if (!addressId.value || !addressDraft.value) return
  savingAddress.value = true
  try {
    await accountApi.updateAddress(addressId.value, addressDraft.value)
    addresses.value = (await accountApi.listAddresses()).data.data
    editingAddress.value = false
  } finally {
    savingAddress.value = false
  }
}

async function confirmOrder(): Promise<void> {
  if (!canSubmit.value) return
  submitting.value = true
  error.value = ''
  try {
    const response = await orderApi.confirm(checkoutPayload(), crypto.randomUUID())
    const url = response.data.data.payment_redirect_url
    if (url) window.location.assign(url)
    else await router.push(`/account/orders/${response.data.data.id}`)
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : 'Đặt hàng thất bại.'
    submitting.value = false
  }
}

watch([platformCoupon, () => JSON.stringify(shopCouponCodes)], () => {
  if (initialized.value) void loadPreview()
})

onMounted(async () => {
  await cartStore.load()
  if (!selectedItemIds.value.length) {
    await router.replace('/cart')
    return
  }
  const [addressResponse, voucherResponse] = await Promise.all([
    accountApi.listAddresses(),
    promotionApi.checkoutVouchers(selectedItemIds.value),
  ])
  addresses.value = addressResponse.data.data
  vouchers.value = voucherResponse.data.data.results
  addressId.value =
    addresses.value.find((address) => address.is_default)?.id ?? addresses.value[0]?.id ?? null
  await loadPreview()
  initialized.value = true
})
</script>

<template>
  <main class="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
    <div>
      <p class="text-sm font-bold uppercase tracking-widest text-indigo-600">CUS-14 · Checkout</p>
      <h1 class="mt-1 text-3xl font-black">Xác nhận và đặt hàng</h1>
    </div>
    <p v-if="error" class="rounded-2xl bg-rose-50 p-4 font-bold text-rose-700">{{ error }}</p>

    <section class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
      <div class="space-y-5">
        <article class="rounded-3xl bg-white p-5 shadow-sm">
          <div class="flex items-center justify-between gap-3">
            <h2 class="text-lg font-black">1. Địa chỉ nhận hàng</h2>
            <RouterLink class="text-sm font-bold text-indigo-600" to="/account/addresses">
              Thêm/quản lý địa chỉ
            </RouterLink>
          </div>
          <select
            v-if="addresses.length"
            v-model="addressId"
            class="mt-4 w-full rounded-xl border border-slate-300 p-3"
          >
            <option v-for="address in addresses" :key="address.id" :value="address.id">
              {{ address.recipient_name }} — {{ address.phone }} — {{ address.detail_address }}
            </option>
          </select>
          <div v-if="selectedAddress && !editingAddress" class="mt-4 rounded-2xl bg-slate-50 p-4">
            <p class="font-black">
              {{ selectedAddress.recipient_name }} · {{ selectedAddress.phone }}
            </p>
            <p class="mt-1 text-sm text-slate-600">
              {{ selectedAddress.detail_address }}, {{ selectedAddress.ward }},
              {{ selectedAddress.district }}, {{ selectedAddress.province }}
            </p>
            <button class="mt-3 text-sm font-bold text-indigo-600" @click="editSelectedAddress">
              Chỉnh sửa địa chỉ này
            </button>
          </div>
          <form
            v-if="editingAddress && addressDraft"
            class="mt-4 grid gap-3 rounded-2xl border border-indigo-200 p-4 sm:grid-cols-2"
            @submit.prevent="saveAddress"
          >
            <input
              v-model.trim="addressDraft.recipient_name"
              required
              class="rounded-xl border p-3"
              placeholder="Người nhận"
            />
            <input
              v-model.trim="addressDraft.phone"
              required
              class="rounded-xl border p-3"
              placeholder="Số điện thoại"
            />
            <input
              v-model.trim="addressDraft.province"
              required
              class="rounded-xl border p-3"
              placeholder="Tỉnh/Thành phố"
            />
            <input
              v-model.trim="addressDraft.district"
              required
              class="rounded-xl border p-3"
              placeholder="Quận/Huyện"
            />
            <input
              v-model.trim="addressDraft.ward"
              required
              class="rounded-xl border p-3"
              placeholder="Phường/Xã"
            />
            <input
              v-model.trim="addressDraft.detail_address"
              required
              class="rounded-xl border p-3"
              placeholder="Địa chỉ cụ thể"
            />
            <div class="flex gap-2 sm:col-span-2">
              <button
                class="rounded-xl bg-indigo-600 px-4 py-2 font-bold text-white"
                :disabled="savingAddress"
              >
                {{ savingAddress ? 'Đang lưu…' : 'Lưu địa chỉ' }}
              </button>
              <button
                type="button"
                class="rounded-xl border px-4 py-2 font-bold"
                @click="editingAddress = false"
              >
                Hủy
              </button>
            </div>
          </form>
          <p v-if="!addresses.length" class="mt-4 rounded-xl bg-amber-50 p-4 text-amber-800">
            Bạn cần thêm địa chỉ nhận hàng trước khi đặt đơn.
          </p>
        </article>

        <article class="rounded-3xl bg-white p-5 shadow-sm">
          <h2 class="text-lg font-black">2. Voucher</h2>
          <label class="mt-4 block text-sm font-bold"
            >Voucher sàn
            <select v-model="platformCoupon" class="mt-1 w-full rounded-xl border p-3 font-normal">
              <option value="">Không sử dụng</option>
              <option
                v-for="voucher in platformVouchers"
                :key="voucher.id"
                :value="voucher.campaign.code"
              >
                {{ voucher.campaign.code }} — {{ voucher.campaign.name }} (ước tính -{{
                  formatCurrency(voucher.estimated_discount)
                }})
              </option>
            </select>
          </label>
          <RouterLink
            class="mt-3 inline-block text-sm font-bold text-indigo-600"
            to="/voucher-center"
            >Lưu thêm voucher</RouterLink
          >
        </article>

        <article
          v-for="shop in preview?.shops ?? []"
          :key="shop.shop_id"
          class="rounded-3xl bg-white p-5 shadow-sm"
        >
          <div class="flex flex-wrap items-center justify-between gap-2">
            <h2 class="text-lg font-black">{{ shop.shop_name }}</h2>
            <b>{{ formatCurrency(shop.total) }}</b>
          </div>
          <div class="mt-4 divide-y">
            <div
              v-for="item in cartStore.cart?.shops
                .find((group) => group.shop_id === shop.shop_id)
                ?.items.filter((entry) => entry.is_selected) ?? []"
              :key="item.id"
              class="flex items-center justify-between gap-3 py-3 text-sm"
            >
              <span
                >{{ item.product_name }} · {{ item.variant_name || item.variant_sku }} ×
                {{ item.quantity }}</span
              >
              <b>{{ formatCurrency(Number(item.current_price) * item.quantity) }}</b>
            </div>
          </div>
          <div class="mt-4 grid gap-4 md:grid-cols-2">
            <label class="text-sm font-bold"
              >Voucher của shop
              <select
                v-model="shopCouponCodes[String(shop.shop_id)]"
                class="mt-1 w-full rounded-xl border p-3 font-normal"
              >
                <option value="">Không sử dụng</option>
                <option
                  v-for="voucher in shopVouchers(shop.shop_id)"
                  :key="voucher.id"
                  :value="voucher.campaign.code"
                >
                  {{ voucher.campaign.code }} — {{ voucher.campaign.name }}
                </option>
              </select>
            </label>
            <label class="text-sm font-bold"
              >Phương thức vận chuyển
              <select
                v-model="shippingMethods[String(shop.shop_id)]"
                class="mt-1 w-full rounded-xl border p-3 font-normal"
              >
                <option value="STANDARD">Giao hàng tiêu chuẩn (phí cố định)</option>
              </select>
            </label>
          </div>
          <label class="mt-4 block text-sm font-bold"
            >Lời nhắn với shop
            <textarea
              v-model.trim="shopNotes[String(shop.shop_id)]"
              maxlength="2000"
              rows="2"
              class="mt-1 w-full rounded-xl border p-3 font-normal"
              placeholder="Ví dụ: Gọi trước khi giao, đóng gói cẩn thận…"
            />
          </label>
          <div class="mt-4 grid grid-cols-2 gap-2 rounded-2xl bg-slate-50 p-4 text-sm">
            <span>Tạm tính</span><b class="text-right">{{ formatCurrency(shop.subtotal) }}</b>
            <span>Phí vận chuyển</span
            ><b class="text-right">{{ formatCurrency(shop.shipping_fee) }}</b>
          </div>
        </article>

        <article class="rounded-3xl bg-white p-5 shadow-sm">
          <h2 class="text-lg font-black">3. Phương thức thanh toán</h2>
          <div class="mt-4 grid gap-3 sm:grid-cols-2">
            <label
              class="cursor-pointer rounded-2xl border p-4"
              :class="paymentMethod === 'COD' && 'border-indigo-500 bg-indigo-50'"
            >
              <input v-model="paymentMethod" value="COD" type="radio" />
              <b class="ml-2">Thanh toán khi nhận hàng (COD)</b>
            </label>
            <label
              class="cursor-pointer rounded-2xl border p-4"
              :class="paymentMethod === 'VNPAY' && 'border-indigo-500 bg-indigo-50'"
            >
              <input v-model="paymentMethod" value="VNPAY" type="radio" />
              <b class="ml-2">VNPay Sandbox</b>
            </label>
          </div>
        </article>
      </div>

      <aside
        class="market-receipt h-fit rounded-2xl bg-[#173b35] p-6 text-white shadow-[0_16px_40px_rgba(23,59,53,0.16)] lg:sticky lg:top-36"
      >
        <h2 class="text-xl font-black">Chi tiết thanh toán</h2>
        <template v-if="preview">
          <p class="mt-5 flex justify-between">
            <span>Tiền hàng</span><b>{{ formatCurrency(preview.subtotal) }}</b>
          </p>
          <p v-if="Number(preview.discount) > 0" class="mt-3 flex justify-between text-[#f2c14e]">
            <span>Voucher</span><b>-{{ formatCurrency(preview.discount) }}</b>
          </p>
          <p class="mt-3 flex justify-between">
            <span>Vận chuyển</span><b>{{ formatCurrency(preview.shipping_total) }}</b>
          </p>
          <p class="mt-5 flex justify-between border-t border-slate-700 pt-5 text-xl">
            <span>Tổng tiền</span><b>{{ formatCurrency(preview.total) }}</b>
          </p>
        </template>
        <div v-else class="mt-5 h-32 animate-pulse rounded-2xl bg-slate-800" />
        <button
          class="market-primary-action mt-6 w-full py-3 disabled:opacity-50"
          :disabled="!canSubmit"
          @click="confirmOrder"
        >
          {{ submitting ? 'Đang đặt hàng…' : 'Đặt hàng' }}
        </button>
        <p v-if="loading" class="mt-3 text-sm text-slate-300">Đang tự động cập nhật tổng tiền…</p>
      </aside>
    </section>
  </main>
</template>
