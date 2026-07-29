const BROWSING_HISTORY_PREFIX = 'mercato:browsing-history'
const MAX_BROWSING_HISTORY_ITEMS = 20
const PRODUCT_ID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

type BrowsingHistoryUserId = string | number | null | undefined

export interface BrowsingHistoryStorage {
  getItem(key: string): string | null
  setItem(key: string, value: string): void
}

export function browsingHistoryStorageKey(userId?: BrowsingHistoryUserId): string {
  const namespace = userId === null || userId === undefined ? 'guest' : `user:${String(userId)}`
  return `${BROWSING_HISTORY_PREFIX}:${namespace}`
}

function browserStorage(): BrowsingHistoryStorage | null {
  try {
    return typeof window === 'undefined' ? null : window.localStorage
  } catch {
    return null
  }
}

function resolveStorage(
  storage: BrowsingHistoryStorage | null | undefined,
): BrowsingHistoryStorage | null {
  return storage === undefined ? browserStorage() : storage
}

function normalizeProductIds(value: unknown): string[] {
  if (!Array.isArray(value)) return []

  const productIds: string[] = []
  const seen = new Set<string>()
  for (const valueItem of value) {
    if (typeof valueItem !== 'string') continue
    const productId = valueItem.trim()
    if (!PRODUCT_ID_PATTERN.test(productId) || seen.has(productId)) continue
    seen.add(productId)
    productIds.push(productId)
    if (productIds.length === MAX_BROWSING_HISTORY_ITEMS) break
  }
  return productIds
}

export function readBrowsingHistory(
  userId?: BrowsingHistoryUserId,
  storage?: BrowsingHistoryStorage | null,
): string[] {
  const targetStorage = resolveStorage(storage)
  if (!targetStorage) return []

  try {
    return normalizeProductIds(
      JSON.parse(targetStorage.getItem(browsingHistoryStorageKey(userId)) ?? '[]'),
    )
  } catch {
    return []
  }
}

export function recordBrowsingProduct(
  productId: string,
  userId?: BrowsingHistoryUserId,
  storage?: BrowsingHistoryStorage | null,
): string[] {
  const normalizedProductId = productId.trim()
  const history = readBrowsingHistory(userId, storage)
  if (!PRODUCT_ID_PATTERN.test(normalizedProductId)) return history

  const nextHistory = [
    normalizedProductId,
    ...history.filter((historyProductId) => historyProductId !== normalizedProductId),
  ].slice(0, MAX_BROWSING_HISTORY_ITEMS)
  const targetStorage = resolveStorage(storage)

  try {
    targetStorage?.setItem(browsingHistoryStorageKey(userId), JSON.stringify(nextHistory))
  } catch {
    // Browsing history is an optional signal; storage failures must never block navigation.
  }
  return nextHistory
}
