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
    ],
  },
]
