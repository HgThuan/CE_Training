<script setup lang="ts">
import {
  ArchiveBoxIcon,
  ArrowPathIcon,
  BellIcon,
  BuildingStorefrontIcon,
  ChatBubbleBottomCenterTextIcon,
  ClipboardDocumentListIcon,
  CubeIcon,
  EnvelopeIcon,
  HomeIcon,
  TicketIcon,
  UserIcon,
  UsersIcon,
} from '@heroicons/vue/24/outline'

import WorkspaceShell from '@/shared/components/WorkspaceShell.vue'

const navigation = [
  {
    label: '',
    items: [{ label: 'Tổng quan kinh doanh', to: '/seller', icon: HomeIcon, exact: true }],
  },
  {
    label: 'Hàng hóa',
    items: [
      { label: 'Sản phẩm', to: '/seller/products', icon: CubeIcon },
      { label: 'Tồn kho', to: '/seller/inventory', icon: ArchiveBoxIcon },
    ],
  },
  {
    label: 'Bán hàng',
    items: [
      { label: 'Đơn hàng', to: '/seller/orders', icon: ClipboardDocumentListIcon },
      { label: 'Trả hàng & hoàn tiền', to: '/seller/returns', icon: ArrowPathIcon },
      { label: 'Khuyến mãi', to: '/seller/promotions', icon: TicketIcon },
    ],
  },
  {
    label: 'Chăm sóc khách hàng',
    items: [
      { label: 'Tin nhắn', to: '/seller/chat', icon: EnvelopeIcon },
      { label: 'Khách hàng', to: '/seller/customers', icon: UsersIcon },
      { label: 'Đánh giá', to: '/seller/reviews', icon: ChatBubbleBottomCenterTextIcon },
    ],
  },
  {
    label: 'Thiết lập',
    items: [
      { label: 'Hồ sơ gian hàng', to: '/seller/shop', icon: BuildingStorefrontIcon },
      { label: 'Hồ sơ cá nhân', to: '/seller/profile', icon: UserIcon },
      { label: 'Thông báo', to: '/seller/notifications', icon: BellIcon },
    ],
  },
]
</script>

<template>
  <WorkspaceShell
    description="Theo dõi đơn, hàng hóa và trải nghiệm khách mua"
    :navigation="navigation"
    notification-to="/seller/notifications"
    profile-to="/seller/profile"
    workspace="seller"
    workspace-label="Seller Center"
  />
</template>
