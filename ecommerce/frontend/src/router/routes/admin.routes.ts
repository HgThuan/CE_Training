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
        component: () => import('@/features/analytics/pages/DashboardPage.vue'),
        props: { mode: 'admin' },
      },
      {
        path: 'operations',
        name: 'admin-operations',
        component: () => import('@/features/analytics/pages/AdminOperationsPage.vue'),
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
      {
        path: 'seller-applications',
        name: 'admin-seller-applications',
        component: () => import('@/features/admin-sellers/pages/SellerApprovalPage.vue'),
      },
      {
        path: 'sellers',
        name: 'admin-sellers',
        component: () => import('@/features/admin-sellers/pages/SellerManagementPage.vue'),
      },
      {
        path: 'products',
        name: 'admin-product-moderation',
        component: () => import('@/features/admin/pages/ProductModerationPage.vue'),
      },
      {
        path: 'categories',
        name: 'admin-categories',
        component: () => import('@/features/admin/pages/CategoryManagerPage.vue'),
      },
      {
        path: 'brands',
        name: 'admin-brands',
        component: () => import('@/features/admin/pages/BrandManagerPage.vue'),
      },
      {
        path: 'banners',
        name: 'admin-banners',
        component: () => import('@/features/admin-banners/pages/BannerListPage.vue'),
      },
      {
        path: 'banners/new',
        name: 'admin-banner-create',
        component: () => import('@/features/admin-banners/pages/BannerFormPage.vue'),
      },
      {
        path: 'banners/:bannerId/edit',
        name: 'admin-banner-edit',
        component: () => import('@/features/admin-banners/pages/BannerFormPage.vue'),
      },
      {
        path: 'orders',
        name: 'admin-orders',
        component: () => import('@/features/admin/order/AdminOrderPage.vue'),
      },
      {
        path: 'disputes',
        name: 'admin-disputes',
        component: () => import('@/features/after-sales/pages/AdminDisputesPage.vue'),
      },
      {
        path: 'review-reports',
        name: 'admin-review-reports',
        component: () => import('@/features/after-sales/pages/AdminReviewReportsPage.vue'),
      },
    ],
  },
]
