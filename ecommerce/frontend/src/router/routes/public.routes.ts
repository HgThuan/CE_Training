import type { RouteRecordRaw } from 'vue-router'

export const publicRoutes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('@/layouts/StorefrontLayout.vue'),
    children: [
      {
        path: '',
        name: 'home',
        component: () => import('@/features/home/pages/HomePage.vue'),
      },
      {
        path: 'shops/:slug',
        name: 'public-shop',
        component: () => import('@/features/shop/pages/PublicShopPage.vue'),
      },
      {
        path: 'shop/:slug',
        redirect: (to) => ({
          name: 'public-shop',
          params: { slug: to.params.slug },
          query: to.query,
          hash: to.hash,
        }),
      },
      {
        path: 'products',
        name: 'product-list',
        component: () => import('@/features/product/pages/ProductListPage.vue'),
      },
      {
        path: 'products/:slug',
        name: 'product-detail',
        component: () => import('@/features/product/pages/ProductDetailPage.vue'),
      },
      {
        path: 'wishlist',
        name: 'wishlist',
        component: () => import('@/features/wishlist/pages/WishlistPage.vue'),
        meta: { requiresAuth: true, roles: ['customer'] },
      },
      {
        path: 'search',
        name: 'search-results',
        component: () => import('@/features/search/pages/SearchResultsPage.vue'),
      },
    ],
  },
  {
    path: '/auth/login',
    name: 'login',
    component: () => import('@/features/auth/pages/LoginPage.vue'),
    meta: { guestOnly: true },
  },
  {
    path: '/auth/register',
    name: 'register',
    component: () => import('@/features/auth/pages/RegisterPage.vue'),
    meta: { guestOnly: true },
  },
  {
    path: '/auth/verify-email',
    name: 'verify-email',
    component: () => import('@/features/auth/pages/VerifyEmailPage.vue'),
  },
  {
    path: '/auth/resend-verification',
    name: 'resend-verification',
    component: () => import('@/features/auth/pages/ResendVerificationPage.vue'),
    meta: { guestOnly: true },
  },
  {
    path: '/auth/forgot-password',
    name: 'forgot-password',
    component: () => import('@/features/auth/pages/ForgotPasswordPage.vue'),
    meta: { guestOnly: true },
  },
  {
    path: '/auth/reset-password',
    name: 'reset-password',
    component: () => import('@/features/auth/pages/ResetPasswordPage.vue'),
    meta: { guestOnly: true },
  },
]
