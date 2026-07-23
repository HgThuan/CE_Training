import type { RouteRecordRaw } from 'vue-router'

export const adminRoutes: RouteRecordRaw[] = [
  {
    path: '/admin',
    component: () => import('@/layouts/AdminLayout.vue'),
    meta: { requiresAuth: true, roles: ['admin'] },
    children: [
      {
        path: '',
        name: 'admin-home',
        component: () => import('@/features/auth/pages/RoleHomePage.vue'),
      },
      {
        path: 'roles',
        name: 'admin-roles',
        component: () => import('@/features/auth/pages/RoleManagementPage.vue'),
      },
      {
        path: 'customers',
        name: 'admin-customers',
        component: () => import('@/features/admin-users/pages/CustomerManagementPage.vue'),
      },
    ],
  },
]
