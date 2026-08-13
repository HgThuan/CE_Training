import { AxiosError } from 'axios'
import { defineStore } from 'pinia'
import { ref } from 'vue'

import { promotionApi } from './api'
import type { FlashSale, FlashSalePayload, Voucher, VoucherPayload, VoucherScope } from './types'

function getApiError(error: unknown): string {
  if (!(error instanceof AxiosError)) return 'Đã có lỗi không mong muốn'
  const payload = error.response?.data as { message?: string } | undefined
  if (error.response?.status === 403) return 'Bạn không có quyền truy cập chức năng này'
  return payload?.message ?? (error.response ? 'Yêu cầu không hợp lệ' : 'Không thể kết nối máy chủ')
}

export const usePromotionStore = defineStore('promotion', () => {
  const vouchers = ref<Voucher[]>([])
  const flashSales = ref<FlashSale[]>([])
  const loading = ref(false)
  const saving = ref(false)
  const error = ref('')

  async function loadVouchers(scope: VoucherScope): Promise<void> {
    loading.value = true
    error.value = ''
    try {
      const response =
        scope === 'platform'
          ? await promotionApi.listAdminVouchers()
          : await promotionApi.listSellerVouchers()
      vouchers.value = response.data.data
    } catch (caught) {
      error.value = getApiError(caught)
    } finally {
      loading.value = false
    }
  }

  async function saveVoucher(
    scope: VoucherScope,
    payload: VoucherPayload,
    id?: string,
  ): Promise<void> {
    saving.value = true
    error.value = ''
    try {
      if (scope === 'platform') {
        if (id) await promotionApi.updateAdminVoucher(id, payload)
        else await promotionApi.createAdminVoucher(payload)
      } else if (id) await promotionApi.updateSellerVoucher(id, payload)
      else await promotionApi.createSellerVoucher(payload)
      await loadVouchers(scope)
    } catch (caught) {
      error.value = getApiError(caught)
      throw caught
    } finally {
      saving.value = false
    }
  }

  async function deleteVoucher(scope: VoucherScope, id: string): Promise<void> {
    if (scope === 'platform') await promotionApi.deleteAdminVoucher(id)
    else await promotionApi.deleteSellerVoucher(id)
    await loadVouchers(scope)
  }

  async function loadAdminFlashSales(): Promise<void> {
    loading.value = true
    error.value = ''
    try {
      flashSales.value = (await promotionApi.listAdminFlashSales()).data.data
    } catch (caught) {
      error.value = getApiError(caught)
    } finally {
      loading.value = false
    }
  }

  async function loadActiveFlashSales(): Promise<void> {
    loading.value = true
    error.value = ''
    try {
      flashSales.value = (await promotionApi.activeFlashSales()).data.data
    } catch (caught) {
      error.value = getApiError(caught)
    } finally {
      loading.value = false
    }
  }

  async function saveFlashSale(payload: FlashSalePayload, id?: string): Promise<void> {
    saving.value = true
    error.value = ''
    try {
      if (id) await promotionApi.updateFlashSale(id, payload)
      else await promotionApi.createFlashSale(payload)
      await loadAdminFlashSales()
    } catch (caught) {
      error.value = getApiError(caught)
      throw caught
    } finally {
      saving.value = false
    }
  }

  async function deleteFlashSale(id: string): Promise<void> {
    await promotionApi.deleteFlashSale(id)
    await loadAdminFlashSales()
  }

  return {
    vouchers,
    flashSales,
    loading,
    saving,
    error,
    loadVouchers,
    saveVoucher,
    deleteVoucher,
    loadAdminFlashSales,
    loadActiveFlashSales,
    saveFlashSale,
    deleteFlashSale,
  }
})
