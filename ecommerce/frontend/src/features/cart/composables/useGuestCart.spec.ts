import { beforeEach, describe, expect, it } from 'vitest'

import { GUEST_CART_STORAGE_KEY, readGuestCart, useGuestCart } from './useGuestCart'

describe('useGuestCart', () => {
  beforeEach(() => localStorage.clear())

  it('reads an empty or corrupt localStorage without crashing', () => {
    expect(readGuestCart()).toEqual([])
    localStorage.setItem(GUEST_CART_STORAGE_KEY, '{broken')
    expect(readGuestCart()).toEqual([])
  })

  it('persists items and accumulates a duplicate variant', () => {
    const cart = useGuestCart()
    cart.add('variant-1', 1)
    cart.add('variant-1', 2)

    expect(readGuestCart()).toMatchObject([{ variant_id: 'variant-1', quantity: 3 }])
  })
})
