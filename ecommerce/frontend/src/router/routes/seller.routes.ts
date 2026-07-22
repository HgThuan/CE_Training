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
    ],
  },
]
