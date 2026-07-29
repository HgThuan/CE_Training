import { vi } from 'vitest'

import {
  browsingHistoryStorageKey,
  type BrowsingHistoryStorage,
  readBrowsingHistory,
  recordBrowsingProduct,
} from './browsingHistory'

function productId(index: number): string {
  return `00000000-0000-4000-8000-${String(index).padStart(12, '0')}`
}

function createStorage() {
  const data = new Map<string, string>()
  const storage: BrowsingHistoryStorage = {
    getItem: vi.fn((key: string) => data.get(key) ?? null),
    setItem: vi.fn((key: string, value: string) => {
      data.set(key, value)
    }),
  }
  return { data, storage }
}

describe('browsing history', () => {
  it('stores newest-first values, deduplicates and keeps at most 20 products', () => {
    const { storage } = createStorage()

    for (let index = 0; index < 25; index += 1) {
      recordBrowsingProduct(productId(index), undefined, storage)
    }
    recordBrowsingProduct(productId(10), undefined, storage)

    const history = readBrowsingHistory(undefined, storage)
    expect(history).toHaveLength(20)
    expect(history[0]).toBe(productId(10))
    expect(new Set(history).size).toBe(20)
    expect(history).not.toContain(productId(4))
  })

  it('isolates guest history and each authenticated user namespace', () => {
    const { storage } = createStorage()
    recordBrowsingProduct(productId(1), undefined, storage)
    recordBrowsingProduct(productId(2), 101, storage)
    recordBrowsingProduct(productId(3), 202, storage)

    expect(readBrowsingHistory(undefined, storage)).toEqual([productId(1)])
    expect(readBrowsingHistory(101, storage)).toEqual([productId(2)])
    expect(readBrowsingHistory(202, storage)).toEqual([productId(3)])
    expect(browsingHistoryStorageKey(101)).not.toBe(browsingHistoryStorageKey(202))
  })

  it('recovers from malformed JSON and sanitizes tampered values', () => {
    const { data, storage } = createStorage()
    const key = browsingHistoryStorageKey()
    data.set(key, '{not-json')

    expect(readBrowsingHistory(undefined, storage)).toEqual([])

    data.set(
      key,
      JSON.stringify([
        productId(1),
        productId(1),
        'not-a-uuid',
        'x'.repeat(10_000),
        ` ${productId(2)} `,
        123,
        null,
      ]),
    )

    expect(readBrowsingHistory(undefined, storage)).toEqual([productId(1), productId(2)])
    expect(recordBrowsingProduct('still-not-a-uuid', undefined, storage)).toEqual([
      productId(1),
      productId(2),
    ])
  })

  it('does not throw when storage access is unavailable', () => {
    const unavailableStorage: BrowsingHistoryStorage = {
      getItem: vi.fn(() => {
        throw new Error('Storage blocked')
      }),
      setItem: vi.fn(() => {
        throw new Error('Quota exceeded')
      }),
    }

    expect(readBrowsingHistory(1, unavailableStorage)).toEqual([])
    expect(recordBrowsingProduct(productId(1), 1, unavailableStorage)).toEqual([productId(1)])
    expect(readBrowsingHistory(1, null)).toEqual([])
    expect(recordBrowsingProduct(productId(2), 1, null)).toEqual([productId(2)])
  })
})
