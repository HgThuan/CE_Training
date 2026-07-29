import { createMemoryHistory, createRouter } from 'vue-router'

import { publicRoutes } from './routes/public.routes'

describe('public storefront routes', () => {
  it('protects wishlist for customers and keeps the plural shop route canonical', () => {
    const root = publicRoutes.find((route) => route.path === '/')
    const wishlist = root?.children?.find((route) => route.name === 'wishlist')
    const publicShop = root?.children?.find((route) => route.name === 'public-shop')

    expect(wishlist?.path).toBe('wishlist')
    expect(wishlist?.meta).toEqual({
      requiresAuth: true,
      roles: ['customer'],
    })
    expect(publicShop?.path).toBe('shops/:slug')
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
