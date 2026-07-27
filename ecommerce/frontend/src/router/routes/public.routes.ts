import type { RouteRecordRaw } from 'vue-router'

export const publicRoutes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'home',
    component: () => import('@/features/home/pages/HomePage.vue'),
  },
  {
    path: '/shop/:slug',
    name: 'public-shop',
    component: () => import('@/features/shop/pages/PublicShopPage.vue'),
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
