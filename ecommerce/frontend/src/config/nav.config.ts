import type { FunctionalComponent, HTMLAttributes, VNodeProps } from 'vue'
import {
  BuildingStorefrontIcon,
  CubeIcon,
  HomeIcon,
  PhotoIcon,
  RectangleStackIcon,
  ScaleIcon,
  ChatBubbleBottomCenterTextIcon,
  TagIcon,
  TicketIcon,
  BoltIcon,
  UsersIcon,
  ChartBarSquareIcon,
  ShieldCheckIcon,
  ClipboardDocumentCheckIcon,
} from '@heroicons/vue/24/outline'

export interface NavItem {
  label: string
  to: string
  icon: FunctionalComponent<HTMLAttributes & VNodeProps>
  exact?: boolean
}

export interface NavGroup {
  label?: string
  items: NavItem[]
}

export const adminNavConfig: NavGroup[] = [
  {
    items: [
      {
        label: 'Tổng quan',
        to: '/admin',
        icon: HomeIcon,
        exact: true,
      },
    ],
  },
  {
    label: 'Sản phẩm',
    items: [
      {
        label: 'Sản phẩm',
        to: '/admin/products',
        icon: CubeIcon,
      },
      {
        label: 'Danh mục',
        to: '/admin/categories',
        icon: RectangleStackIcon,
      },
      {
        label: 'Thương hiệu',
        to: '/admin/brands',
        icon: TagIcon,
      },
    ],
  },
  {
    label: 'Marketing',
    items: [
      {
        label: 'Voucher',
        to: '/admin/vouchers',
        icon: TicketIcon,
      },
      {
        label: 'Flash Sale',
        to: '/admin/flash-sales',
        icon: BoltIcon,
      },
      {
        label: 'Banner',
        to: '/admin/banners',
        icon: PhotoIcon,
      },
    ],
  },
  {
    label: 'Vận hành',
    items: [
      {
        label: 'Tranh chấp',
        to: '/admin/disputes',
        icon: ScaleIcon,
      },
      {
        label: 'Báo cáo review',
        to: '/admin/review-reports',
        icon: ChatBubbleBottomCenterTextIcon,
      },
      {
        label: 'Báo cáo',
        to: '/admin/operations',
        icon: ChartBarSquareIcon,
      },
    ],
  },
  {
    label: 'Người dùng',
    items: [
      {
        label: 'Phân quyền',
        to: '/admin/roles',
        icon: ShieldCheckIcon,
      },
      {
        label: 'Khách hàng',
        to: '/admin/customers',
        icon: UsersIcon,
      },
      {
        label: 'Duyệt đăng ký',
        to: '/admin/seller-applications',
        icon: ClipboardDocumentCheckIcon,
      },
      {
        label: 'Seller',
        to: '/admin/sellers',
        icon: BuildingStorefrontIcon,
      },
    ],
  },
]
