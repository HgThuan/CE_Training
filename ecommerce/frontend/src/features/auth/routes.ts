import type { UserRole } from './types'

export function homePathForRole(role: UserRole): string {
  const paths: Record<UserRole, string> = {
    admin: '/admin',
    seller: '/seller',
    customer: '/account/profile',
  }
  return paths[role]
}
