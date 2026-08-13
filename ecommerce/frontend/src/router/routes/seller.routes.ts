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
        path: 'products',
        name: 'seller-products',
        component: () => import('@/features/seller/pages/ProductListPage.vue'),
      },
      {
        path: 'products/new',
        name: 'seller-product-create',
        component: () => import('@/features/seller/pages/ProductFormPage.vue'),
      },
      {
        path: 'products/:productId/edit',
        name: 'seller-product-edit',
        component: () => import('@/features/seller/pages/ProductFormPage.vue'),
      },
      {
        path: 'inventory',
        name: 'seller-inventory',
        component: () => import('@/features/inventory/views/InventoryList.vue'),
      },
      {
        path: 'inventory/entries',
        name: 'seller-stock-entries',
        component: () => import('@/features/inventory/views/StockEntryList.vue'),
      },
      {
        path: 'inventory/out',
        name: 'seller-stock-out-entries',
        component: () => import('@/features/inventory/views/StockOutEntryList.vue'),
      },
      {
        path: 'inventory/movements',
        name: 'seller-stock-movements',
        component: () => import('@/features/inventory/views/StockMovementHistory.vue'),
      },
      {
        path: 'application',
        name: 'seller-application-status',
        component: () => import('@/features/seller/pages/SellerApplicationPage.vue'),
      },
      {
        path: 'orders',
        name: 'seller-orders',
        component: () => import('@/features/seller/order/SellerOrderPage.vue'),
      },
      {
        path: 'customers',
        name: 'seller-customers',
        component: () => import('@/features/after-sales/pages/SellerCustomersPage.vue'),
      },
      {
        path: 'reviews',
        name: 'seller-reviews',
        component: () => import('@/features/after-sales/pages/SellerReviewsPage.vue'),
      },
      {
        path: 'returns',
        name: 'seller-returns',
        component: () => import('@/features/after-sales/pages/SellerReturnsPage.vue'),
      },
      {
        path: 'chat',
        name: 'seller-chat',
        component: () => import('@/features/chat/pages/ChatPage.vue'),
      },
      {
        path: 'notifications',
        name: 'seller-notifications',
        component: () => import('@/features/notification/pages/NotificationCenterPage.vue'),
      },
    ],
  },
]
