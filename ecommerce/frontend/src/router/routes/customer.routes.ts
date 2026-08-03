import type { RouteRecordRaw } from 'vue-router'

export const customerRoutes: RouteRecordRaw[] = [
  {
    path: '/account',
    component: () => import('@/layouts/CustomerLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/account/profile' },
      {
        path: 'profile',
        name: 'profile',
        component: () => import('@/features/auth/pages/ProfilePage.vue'),
      },
      {
        path: 'addresses',
        name: 'account-addresses',
        component: () => import('@/features/account/pages/AddressBookPage.vue'),
        meta: { roles: ['customer'] },
      },
      {
        path: 'seller-application',
        name: 'seller-application',
        component: () => import('@/features/seller/pages/SellerApplicationPage.vue'),
        meta: { roles: ['customer'] },
      },
      {
        path: 'orders',
        name: 'customer-orders',
        component: () => import('@/features/order/pages/OrderListPage.vue'),
        meta: { roles: ['customer'] },
      },
      {
        path: 'orders/:orderId',
        name: 'customer-order-detail',
        component: () => import('@/features/order/pages/OrderDetailPage.vue'),
        meta: { roles: ['customer'] },
      },
    ],
  },
]
