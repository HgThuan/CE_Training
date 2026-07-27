import type { RouteRecordRaw } from 'vue-router'

export const sellerRoutes: RouteRecordRaw[] = [
  {
    path: '/seller',
    component: () => import('@/layouts/SellerLayout.vue'),
    meta: { requiresAuth: true, roles: ['seller'] },
    children: [
      {
        path: '',
        name: 'seller-home',
        component: () => import('@/features/auth/pages/RoleHomePage.vue'),
      },
      {
        path: 'shop',
        name: 'seller-shop',
        component: () => import('@/features/seller/pages/ShopProfilePage.vue'),
      },
      {
        path: 'application',
        name: 'seller-application-status',
        component: () => import('@/features/seller/pages/SellerApplicationPage.vue'),
      },
    ],
  },
]
