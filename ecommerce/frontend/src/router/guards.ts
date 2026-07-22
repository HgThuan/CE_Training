import type { Router } from 'vue-router'

import { homePathForRole } from '@/features/auth/routes'
import { useAuthStore } from '@/stores/auth'

export function registerRoleGuards(router: Router): void {
  router.beforeEach(async (to) => {
    const authStore = useAuthStore()
    if (!authStore.initialized) await authStore.restoreSession()

    if (to.meta.guestOnly && authStore.user) {
      return homePathForRole(authStore.user.role)
    }

    if (to.meta.requiresAuth && !authStore.isAuthenticated) {
      return { path: '/auth/login', query: { redirect: to.fullPath } }
    }

    if (to.meta.roles && authStore.user && !to.meta.roles.includes(authStore.user.role)) {
      return homePathForRole(authStore.user.role)
    }

    return true
  })
}
