<script setup lang="ts">
import {
  BoltIcon,
  BuildingStorefrontIcon,
  ChartBarSquareIcon,
  ChatBubbleBottomCenterTextIcon,
  CheckBadgeIcon,
  ClipboardDocumentListIcon,
  CubeIcon,
  HomeIcon,
  PhotoIcon,
  RectangleStackIcon,
  ScaleIcon,
  ShieldCheckIcon,
  TagIcon,
  TicketIcon,
  UsersIcon,
} from '@heroicons/vue/24/outline'

import WorkspaceShell from '@/shared/components/WorkspaceShell.vue'
import ChatWidget from '@/features/ai-chat/components/ChatWidget.vue'

const navigation = [
  {
    label: '',
    items: [{ label: 'Tổng quan', to: '/admin', icon: HomeIcon, exact: true }],
  },
  {
    label: 'Danh mục & nội dung',
    items: [
      { label: 'Kiểm duyệt sản phẩm', to: '/admin/products', icon: CubeIcon },
      { label: 'Danh mục', to: '/admin/categories', icon: RectangleStackIcon },
      { label: 'Thương hiệu', to: '/admin/brands', icon: TagIcon },
    ],
  },
  {
    label: 'Tăng trưởng',
    items: [
      { label: 'Voucher', to: '/admin/vouchers', icon: TicketIcon },
      { label: 'Flash sale', to: '/admin/flash-sales', icon: BoltIcon },
      { label: 'Banner trang chủ', to: '/admin/banners', icon: PhotoIcon },
    ],
  },
  {
    label: 'Vận hành & chất lượng',
    items: [
      { label: 'Đơn hàng', to: '/admin/orders', icon: ClipboardDocumentListIcon },
      { label: 'Tranh chấp', to: '/admin/disputes', icon: ScaleIcon },
      {
        label: 'Báo cáo đánh giá',
        to: '/admin/review-reports',
        icon: ChatBubbleBottomCenterTextIcon,
      },
      { label: 'Báo cáo hệ thống', to: '/admin/operations', icon: ChartBarSquareIcon },
    ],
  },
  {
    label: 'Tài khoản & phân quyền',
    items: [
      { label: 'Khách hàng', to: '/admin/customers', icon: UsersIcon },
      { label: 'Nhà bán hàng', to: '/admin/sellers', icon: BuildingStorefrontIcon },
      { label: 'Hồ sơ chờ duyệt', to: '/admin/seller-applications', icon: CheckBadgeIcon },
      { label: 'Vai trò & quyền', to: '/admin/roles', icon: ShieldCheckIcon },
    ],
  },
]
</script>

<template>
  <WorkspaceShell
    description="Kiểm soát dữ liệu và vận hành toàn sàn"
    :navigation="navigation"
    workspace="admin"
    workspace-label="Admin Console"
  />
  <ChatWidget />
</template>
