<script setup lang="ts">
import { ArrowLeftIcon } from '@heroicons/vue/24/outline'
import { computed, nextTick, onMounted, ref } from 'vue'

import { analyticsApi } from '@/features/analytics/api'
import type { AuditEntry } from '@/features/analytics/types'
import { confirmDialog } from '@/shared/composables/useAppDialog'
import type { PaginationMeta } from '@/shared/types/api'
import { useAuthStore } from '@/stores/auth'

import { authApi } from '../api'
import FormMessage from '../components/FormMessage.vue'
import { getErrorMessage } from '../errors'
import type { RoleAssignableUser, UserRole } from '../types'

const authStore = useAuthStore()
const users = ref<RoleAssignableUser[]>([])
const selectedUser = ref<RoleAssignableUser | null>(null)
const rolePanel = ref<HTMLElement | null>(null)
const auditLogs = ref<AuditEntry[]>([])
const search = ref('')
const roleFilter = ref<'' | UserRole>('')
const statusFilter = ref<'all' | 'active' | 'locked'>('all')
const role = ref<UserRole>('customer')
const meta = ref<PaginationMeta>({ page: 1, page_size: 20, total_items: 0, total_pages: 1 })
const loading = ref(false)
const saving = ref(false)
const auditLoading = ref(false)
const message = ref('')
const errorMessage = ref('')
const auditError = ref('')

const roleLabels: Record<UserRole, string> = {
  customer: 'Khách hàng',
  seller: 'Người bán',
  admin: 'Quản trị viên',
}

const isCurrentUser = computed(() => selectedUser.value?.id === authStore.user?.id)

function displayName(user: RoleAssignableUser): string {
  return user.full_name.trim() || user.email.split('@')[0] || user.email
}

function roleBadgeClasses(userRole: UserRole): string {
  return {
    admin: 'bg-indigo-50 text-indigo-700 ring-indigo-200',
    seller: 'bg-amber-50 text-amber-800 ring-amber-200',
    customer: 'bg-slate-100 text-slate-700 ring-slate-200',
  }[userRole]
}

function roleChangeLabel(entry: AuditEntry): string {
  const change = entry.diff?.role
  if (!change || typeof change !== 'object') return 'Vai trò đã được cập nhật'
  const values = change as Record<string, unknown>
  const before = typeof values.before === 'string' ? values.before : ''
  const after = typeof values.after === 'string' ? values.after : ''
  const beforeLabel = before in roleLabels ? roleLabels[before as UserRole] : before
  const afterLabel = after in roleLabels ? roleLabels[after as UserRole] : after
  return beforeLabel && afterLabel ? `${beforeLabel} → ${afterLabel}` : 'Vai trò đã được cập nhật'
}

async function loadUsers(page = 1): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  try {
    const response = await authApi.roleUsers({
      search: search.value || undefined,
      role: roleFilter.value || undefined,
      is_active: statusFilter.value === 'all' ? undefined : statusFilter.value === 'active',
      page,
      page_size: 20,
    })
    users.value = response.data.data
    meta.value =
      response.data.meta ??
      ({
        page,
        page_size: 20,
        total_items: response.data.data.length,
        total_pages: 1,
      } satisfies PaginationMeta)
    if (selectedUser.value && !users.value.some((user) => user.id === selectedUser.value?.id)) {
      selectedUser.value = null
      auditLogs.value = []
    }
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
}

async function loadAuditLogs(userId: number): Promise<void> {
  auditLoading.value = true
  auditError.value = ''
  try {
    const response = await analyticsApi.auditLogs({
      action: 'assign_role',
      target_type: 'User',
      target_id: String(userId),
    })
    auditLogs.value = response.data.data.slice(0, 5)
  } catch (error) {
    auditError.value = getErrorMessage(error)
  } finally {
    auditLoading.value = false
  }
}

async function selectUser(user: RoleAssignableUser): Promise<void> {
  selectedUser.value = user
  role.value = user.role
  auditLogs.value = []
  message.value = ''
  errorMessage.value = ''
  await nextTick()
  if (typeof window.matchMedia === 'function' && window.matchMedia('(max-width: 1023px)').matches) {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    rolePanel.value?.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' })
  }
  await loadAuditLogs(user.id)
}

async function assignRole(): Promise<void> {
  if (!selectedUser.value || isCurrentUser.value || role.value === selectedUser.value.role) return

  const target = selectedUser.value
  const oldRole = target.role
  const nextRole = role.value
  const confirmed = await confirmDialog({
    title: oldRole === 'admin' ? 'Xác nhận hạ quyền quản trị viên' : 'Xác nhận thay đổi vai trò',
    message: `${displayName(target)} (${target.email}) sẽ chuyển từ ${roleLabels[oldRole]} sang ${roleLabels[nextRole]}. Toàn bộ phiên đăng nhập hiện tại của tài khoản này sẽ bị vô hiệu hóa.`,
    confirmLabel: 'Xác nhận đổi vai trò',
    destructive: oldRole === 'admin' && nextRole !== 'admin',
  })
  if (!confirmed) return

  saving.value = true
  message.value = ''
  errorMessage.value = ''
  try {
    const response = await authApi.assignRole(target.id, nextRole)
    const updatedRole = response.data.data.role
    selectedUser.value = { ...target, role: updatedRole }
    role.value = updatedRole
    users.value = users.value.map((user) =>
      user.id === response.data.data.id ? { ...user, role: updatedRole } : user,
    )
    message.value = response.data.message
    await loadAuditLogs(target.id)
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    saving.value = false
  }
}

onMounted(() => loadUsers())
</script>

<template>
  <div class="mx-auto max-w-6xl py-2 sm:py-4">
    <RouterLink
      class="inline-flex min-h-11 items-center gap-2 font-semibold text-indigo-700 transition-colors hover:text-indigo-900 focus:outline-none focus:ring-2 focus:ring-indigo-300"
      to="/admin"
    >
      <ArrowLeftIcon class="h-4 w-4" aria-hidden="true" />
      Admin workspace
    </RouterLink>

    <header class="mt-4 max-w-3xl">
      <h1 class="text-3xl font-black tracking-tight text-slate-950 sm:text-4xl">
        Phân quyền người dùng
      </h1>
      <p class="mt-3 text-sm leading-6 text-slate-600">
        Tìm đúng tài khoản, kiểm tra vai trò hiện tại rồi xác nhận quyền truy cập mới. Mọi thay đổi
        đều vô hiệu các phiên cũ và được lưu trong nhật ký kiểm toán.
      </p>
    </header>

    <FormMessage v-if="message" class="mt-6" :message="message" variant="success" />
    <FormMessage v-if="errorMessage" class="mt-6" :message="errorMessage" />

    <div class="mt-8 grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_22rem] xl:gap-8">
      <section
        class="min-w-0 rounded-2xl bg-white p-4 ring-1 ring-slate-200 sm:p-6"
        aria-labelledby="user-search-heading"
      >
        <h2 id="user-search-heading" class="text-lg font-bold text-slate-950">
          Danh sách người dùng
        </h2>
        <p class="mt-1 text-sm text-slate-500">
          Lọc danh sách trước khi chọn tài khoản cần phân quyền.
        </p>
        <form
          class="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-[minmax(0,1fr)_11rem_11rem_auto]"
          role="search"
          @submit.prevent="loadUsers()"
        >
          <label class="block">
            <span class="text-sm font-medium text-gray-800">Tìm kiếm chi tiết</span>
            <input
              id="role-user-search"
              v-model.trim="search"
              class="mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-950 outline-none placeholder:text-slate-400 focus:border-indigo-600 focus:ring-2 focus:ring-indigo-200"
              placeholder="Tên, email hoặc số điện thoại"
              type="search"
            />
          </label>
          <label class="block">
            <span class="text-sm font-medium text-gray-800">Vai trò hiện tại</span>
            <select
              id="role-filter"
              v-model="roleFilter"
              class="mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-950 outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-200"
            >
              <option value="">Tất cả vai trò</option>
              <option value="customer">Khách hàng</option>
              <option value="seller">Người bán</option>
              <option value="admin">Quản trị viên</option>
            </select>
          </label>
          <label class="block">
            <span class="text-sm font-medium text-gray-800">Trạng thái</span>
            <select
              id="status-filter"
              v-model="statusFilter"
              class="mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-slate-950 outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-200"
            >
              <option value="all">Tất cả trạng thái</option>
              <option value="active">Đang hoạt động</option>
              <option value="locked">Đã khóa</option>
            </select>
          </label>
          <button
            class="min-h-11 self-end rounded-xl bg-slate-950 px-5 py-3 font-semibold text-white hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-400 disabled:cursor-not-allowed disabled:opacity-60"
            type="submit"
            :disabled="loading"
          >
            {{ loading ? 'Đang tìm…' : 'Tìm kiếm' }}
          </button>
        </form>

        <p v-if="loading" class="mt-6 py-8 text-center text-sm text-slate-600" role="status">
          Đang tải danh sách người dùng…
        </p>
        <p
          v-else-if="users.length === 0"
          class="mt-6 rounded-xl bg-slate-50 p-5 text-sm leading-6 text-slate-700"
        >
          Không tìm thấy tài khoản phù hợp. Hãy điều chỉnh từ khóa, vai trò hoặc trạng thái.
        </p>
        <div v-else class="mt-6 flex flex-wrap items-center justify-between gap-2">
          <p class="text-sm font-semibold text-slate-700">{{ meta.total_items }} người dùng</p>
          <p class="text-xs text-slate-500">Trang {{ meta.page }}/{{ meta.total_pages }}</p>
        </div>
        <ul v-if="!loading && users.length" class="mt-2 divide-y divide-slate-100">
          <li v-for="user in users" :key="user.id">
            <div
              class="grid gap-4 rounded-xl px-3 py-4 sm:grid-cols-[minmax(0,1fr)_9rem_auto] sm:items-center"
              :class="
                selectedUser?.id === user.id
                  ? 'bg-indigo-50 ring-2 ring-inset ring-indigo-500'
                  : 'hover:bg-slate-50'
              "
            >
              <div class="min-w-0">
                <span class="block truncate font-semibold text-gray-950">
                  {{ displayName(user) }}
                </span>
                <span class="mt-1 block truncate text-sm text-slate-600">{{ user.email }}</span>
                <span class="mt-1 block text-xs text-slate-500">
                  {{ user.phone || 'Chưa cập nhật số điện thoại' }}
                </span>
                <span
                  v-if="user.id === authStore.user?.id"
                  class="mt-2 inline-flex rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-900"
                >
                  Đây là tài khoản của bạn
                </span>
              </div>
              <div class="flex flex-wrap items-center gap-2 sm:flex-col sm:items-end">
                <span
                  class="inline-flex rounded-full px-2.5 py-1 text-xs font-bold ring-1 ring-inset"
                  :class="roleBadgeClasses(user.role)"
                >
                  {{ roleLabels[user.role] }}
                </span>
                <span
                  class="inline-flex rounded-full px-2.5 py-1 text-xs font-semibold"
                  :class="
                    user.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'
                  "
                >
                  {{ user.is_active ? 'Đang hoạt động' : 'Đã khóa' }}
                </span>
              </div>
              <button
                class="min-h-11 justify-self-start rounded-xl border border-indigo-600 px-4 py-2 text-sm font-semibold text-indigo-700 hover:bg-indigo-600 hover:text-white focus:outline-none focus:ring-2 focus:ring-indigo-300 sm:justify-self-end"
                type="button"
                :aria-label="`Phân quyền cho ${displayName(user)}`"
                :aria-pressed="selectedUser?.id === user.id"
                @click="selectUser(user)"
              >
                {{ selectedUser?.id === user.id ? 'Đang phân quyền' : 'Phân quyền' }}
              </button>
            </div>
          </li>
        </ul>

        <nav
          v-if="!loading && meta.total_pages > 1"
          class="mt-5 grid grid-cols-[auto_1fr_auto] items-center gap-3 border-t border-slate-100 pt-5"
          aria-label="Phân trang người dùng"
        >
          <button
            class="min-h-11 rounded-xl border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
            type="button"
            :disabled="meta.page <= 1"
            @click="loadUsers(meta.page - 1)"
          >
            Trước
          </button>
          <span class="text-center text-xs text-slate-600 sm:text-sm">
            Trang {{ meta.page }}/{{ meta.total_pages }}
          </span>
          <button
            class="min-h-11 rounded-xl border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
            type="button"
            :disabled="meta.page >= meta.total_pages"
            @click="loadUsers(meta.page + 1)"
          >
            Sau
          </button>
        </nav>
      </section>

      <aside
        ref="rolePanel"
        class="scroll-mt-20 self-start rounded-2xl bg-white p-5 ring-1 ring-slate-200 sm:p-6 lg:sticky lg:top-6"
      >
        <h2 class="text-lg font-bold text-slate-950">Cấp vai trò</h2>
        <p v-if="!selectedUser" class="mt-3 text-sm leading-6 text-gray-600">
          Chọn nút “Phân quyền” bên cạnh một tài khoản để xem và cập nhật đúng vai trò hiện tại.
        </p>
        <form v-else class="mt-4 space-y-5" @submit.prevent="assignRole">
          <div class="rounded-xl bg-slate-50 p-4 text-sm">
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <p class="truncate font-bold text-slate-950">{{ displayName(selectedUser) }}</p>
                <p class="mt-1 break-all text-slate-600">{{ selectedUser.email }}</p>
              </div>
              <span
                class="shrink-0 rounded-full px-2.5 py-1 text-xs font-bold ring-1 ring-inset"
                :class="roleBadgeClasses(selectedUser.role)"
              >
                {{ roleLabels[selectedUser.role] }}
              </span>
            </div>
          </div>
          <p
            v-if="isCurrentUser"
            class="rounded-xl bg-amber-50 p-4 text-sm leading-6 text-amber-900"
            role="alert"
          >
            Đây là tài khoản bạn đang sử dụng. Vì an toàn, bạn không thể tự thay đổi vai trò của
            chính mình; hãy nhờ một quản trị viên khác thực hiện.
          </p>
          <label class="block text-sm font-medium text-slate-800">
            Vai trò mới
            <select
              id="assigned-role"
              v-model="role"
              class="mt-2 w-full rounded-xl border border-gray-300 bg-white px-4 py-3 outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-200 disabled:cursor-not-allowed disabled:bg-gray-100"
              :disabled="isCurrentUser"
            >
              <option value="customer">Khách hàng</option>
              <option value="seller">Người bán</option>
              <option value="admin">Quản trị viên</option>
            </select>
          </label>
          <p
            v-if="!isCurrentUser && role === selectedUser.role"
            class="text-xs leading-5 text-slate-500"
          >
            Chọn một vai trò khác để bật nút cập nhật.
          </p>
          <button
            class="w-full rounded-xl bg-indigo-600 px-5 py-3 font-semibold text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-300 disabled:cursor-not-allowed disabled:opacity-60"
            type="submit"
            :disabled="saving || isCurrentUser || role === selectedUser.role"
          >
            {{ saving ? 'Đang cập nhật…' : 'Cập nhật vai trò' }}
          </button>
        </form>

        <section
          v-if="selectedUser"
          class="mt-6 border-t border-slate-200 pt-5"
          aria-labelledby="role-audit-heading"
        >
          <div class="flex items-center justify-between gap-3">
            <h3 id="role-audit-heading" class="font-bold text-slate-950">
              Lịch sử phân quyền gần đây
            </h3>
            <RouterLink
              class="inline-flex min-h-11 items-center text-sm font-semibold text-indigo-700 hover:text-indigo-900 focus:outline-none focus:ring-2 focus:ring-indigo-300"
              to="/admin/operations"
            >
              Xem tất cả
            </RouterLink>
          </div>
          <p v-if="auditLoading" class="mt-3 text-sm text-gray-600" role="status">
            Đang tải lịch sử…
          </p>
          <p v-else-if="auditError" class="mt-3 text-sm text-rose-700">{{ auditError }}</p>
          <p v-else-if="auditLogs.length === 0" class="mt-3 text-sm text-gray-600">
            Chưa có thay đổi vai trò nào được ghi nhận.
          </p>
          <ol v-else class="mt-3 divide-y divide-slate-100">
            <li v-for="entry in auditLogs" :key="entry.id" class="py-3 text-sm text-slate-700">
              <p class="font-semibold text-slate-900">{{ roleChangeLabel(entry) }}</p>
              <p class="mt-1 truncate text-xs text-slate-500">{{ entry.actor }}</p>
              <time class="mt-1 block text-xs text-slate-500" :datetime="entry.created_at">
                {{ new Date(entry.created_at).toLocaleString('vi-VN') }}
              </time>
            </li>
          </ol>
        </section>
      </aside>
    </div>
  </div>
</template>
