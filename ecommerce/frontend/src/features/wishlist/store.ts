import { defineStore } from 'pinia'
import { reactive, ref, watch } from 'vue'

import type { PaginationMeta } from '@/shared/types/api'
import { useAuthStore } from '@/stores/auth'

import { wishlistApi } from './api'
import type { WishlistItem, WishlistToggleResult } from './types'

const EMPTY_META: PaginationMeta = {
  page: 1,
  page_size: 12,
  total_items: 0,
  total_pages: 0,
}

export const useWishlistStore = defineStore('wishlist', () => {
  const authStore = useAuthStore()
  const items = ref<WishlistItem[]>([])
  const meta = ref<PaginationMeta>({ ...EMPTY_META })
  const memberIds = reactive(new Set<string>())
  const pendingIds = reactive(new Set<string>())
  const loading = ref(false)
  const hydrating = ref(false)
  const pageLoaded = ref(false)
  const hydratedUserId = ref<number | null>(null)
  let listRequestSequence = 0
  let hydrationRequestSequence = 0

  function isWishlisted(productId: string): boolean {
    return memberIds.has(productId)
  }

  function isPending(productId: string): boolean {
    return pendingIds.has(productId)
  }

  function reset(): void {
    listRequestSequence += 1
    hydrationRequestSequence += 1
    items.value = []
    meta.value = { ...EMPTY_META }
    memberIds.clear()
    pendingIds.clear()
    loading.value = false
    hydrating.value = false
    pageLoaded.value = false
    hydratedUserId.value = null
  }

  async function loadPage(page = 1, pageSize = 12): Promise<void> {
    const sequence = ++listRequestSequence
    loading.value = true
    try {
      const response = await wishlistApi.list({ page, page_size: pageSize })
      if (sequence !== listRequestSequence) return
      items.value = response.data.data
      meta.value = response.data.meta ?? {
        page,
        page_size: pageSize,
        total_items: items.value.length,
        total_pages: items.value.length ? 1 : 0,
      }
      pageLoaded.value = true
      for (const item of items.value) memberIds.add(item.product.id)
    } finally {
      if (sequence === listRequestSequence) loading.value = false
    }
  }

  async function hydrateMembership(force = false): Promise<void> {
    const user = authStore.user
    if (!user || user.role !== 'customer') {
      if (hydratedUserId.value !== null || memberIds.size) reset()
      return
    }
    if (!force && (hydratedUserId.value === user.id || hydrating.value)) return

    const sequence = ++hydrationRequestSequence
    hydrating.value = true
    try {
      const first = await wishlistApi.list({ page: 1, page_size: 100 })
      const totalPages = first.data.meta?.total_pages ?? 1
      const remaining =
        totalPages > 1
          ? await Promise.all(
              Array.from({ length: totalPages - 1 }, (_, index) =>
                wishlistApi.list({ page: index + 2, page_size: 100 }),
              ),
            )
          : []
      if (
        sequence !== hydrationRequestSequence ||
        authStore.user?.id !== user.id ||
        authStore.user.role !== 'customer'
      ) {
        return
      }
      const nextIds = [
        ...first.data.data,
        ...remaining.flatMap((response) => response.data.data),
      ].map((item) => item.product.id)
      memberIds.clear()
      for (const productId of nextIds) memberIds.add(productId)
      hydratedUserId.value = user.id
    } finally {
      if (sequence === hydrationRequestSequence) hydrating.value = false
    }
  }

  async function toggle(productId: string): Promise<WishlistToggleResult> {
    if (pendingIds.has(productId)) {
      return {
        product_id: productId,
        is_wishlisted: memberIds.has(productId),
        item: null,
      }
    }

    pendingIds.add(productId)
    try {
      const result = (await wishlistApi.toggle(productId)).data.data
      if (result.is_wishlisted) memberIds.add(productId)
      else memberIds.delete(productId)
      if (authStore.user?.role === 'customer') hydratedUserId.value = authStore.user.id

      if (pageLoaded.value) {
        const existingIndex = items.value.findIndex((item) => item.product.id === productId)
        if (result.is_wishlisted && result.item && existingIndex === -1) {
          items.value.unshift(result.item)
          meta.value.total_items += 1
        } else if (!result.is_wishlisted && existingIndex >= 0) {
          items.value.splice(existingIndex, 1)
          meta.value.total_items = Math.max(meta.value.total_items - 1, 0)
        }
        meta.value.total_pages = Math.ceil(meta.value.total_items / meta.value.page_size)
      }
      return result
    } finally {
      pendingIds.delete(productId)
    }
  }

  watch(
    () => authStore.user?.id ?? null,
    () => reset(),
  )

  return {
    items,
    meta,
    loading,
    hydrating,
    isWishlisted,
    isPending,
    loadPage,
    hydrateMembership,
    toggle,
    reset,
  }
})
