import { createMemoryHistory, createRouter } from 'vue-router'

import { publicRoutes } from './routes/public.routes'

describe('public storefront routes', () => {
  it('protects wishlist for customers and keeps the plural shop route canonical', () => {
    const root = publicRoutes.find((route) => route.path === '/')
    const wishlist = root?.children?.find((route) => route.name === 'wishlist')
    const publicShop = root?.children?.find((route) => route.name === 'public-shop')
    const checkout = root?.children?.find((route) => route.name === 'checkout')
    const paymentReturn = publicRoutes.find((route) => route.name === 'payment-return')

    expect(wishlist?.path).toBe('wishlist')
    expect(wishlist?.meta).toEqual({
      requiresAuth: true,
      roles: ['customer'],
    })
    expect(publicShop?.path).toBe('shops/:slug')
    expect(checkout?.path).toBe('checkout')
    expect(checkout?.meta).toEqual({ requiresAuth: true, roles: ['customer'] })
    expect(paymentReturn?.path).toBe('/payment/return')
  })

  it('redirects legacy singular shop links without losing query or hash', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: publicRoutes,
    })

    await router.push('/shop/future-shop?sort=rating#products')
    await router.isReady()

    expect(router.currentRoute.value.fullPath).toBe('/shops/future-shop?sort=rating#products')
  })
})
