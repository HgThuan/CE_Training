import { createRouter, createWebHistory } from 'vue-router'

import { adminRoutes } from './routes/admin.routes'
import { customerRoutes } from './routes/customer.routes'
import { publicRoutes } from './routes/public.routes'
import { sellerRoutes } from './routes/seller.routes'
import { registerRoleGuards } from './guards'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [...publicRoutes, ...customerRoutes, ...sellerRoutes, ...adminRoutes],
  scrollBehavior: () => ({ top: 0 }),
})

registerRoleGuards(router)

export default router
