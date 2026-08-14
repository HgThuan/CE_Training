<script setup lang="ts">
import {
  ArrowRightIcon,
  CheckBadgeIcon,
  MagnifyingGlassIcon,
  ShoppingBagIcon,
  SparklesIcon,
  TagIcon,
  TruckIcon,
} from '@heroicons/vue/24/outline'

import heroImage from '@/assets/market-hero.png'

const categoryEntries = ['Điện tử', 'Thời trang', 'Nhà cửa']
const promises = [
  { label: 'Tìm kiếm có AI', icon: SparklesIcon },
  { label: 'Giỏ hàng đa shop', icon: ShoppingBagIcon },
  { label: 'Voucher đúng phạm vi', icon: TagIcon },
  { label: 'Theo dõi đơn tập trung', icon: TruckIcon },
  { label: 'Sản phẩm kiểm duyệt', icon: CheckBadgeIcon },
]
</script>

<template>
  <section aria-labelledby="market-hero-heading">
    <div class="market-trust-rail" aria-label="Điểm nổi bật của Mercato">
      <div v-for="item in promises" :key="item.label">
        <component :is="item.icon" class="size-5" />
        <span>{{ item.label }}</span>
      </div>
    </div>

    <div class="market-curated-hero">
      <img :src="heroImage" alt="Tuyển chọn điện tử, thời trang và đồ dùng nhà cửa" />
      <div class="market-curated-hero__content">
        <h1 id="market-hero-heading">Mọi thứ bạn cần, trong một lần ghé.</h1>
        <p>
          Tìm giữa nhiều gian hàng, so sánh lựa chọn và hoàn tất đơn mua trong một hành trình thống
          nhất.
        </p>
        <ul>
          <li>
            <MagnifyingGlassIcon class="size-5" /> Tìm sản phẩm bằng từ khóa hoặc ngôn ngữ tự nhiên
          </li>
          <li><TagIcon class="size-5" /> Giá và ưu đãi được trình bày rõ ràng</li>
          <li><TruckIcon class="size-5" /> Theo dõi đơn hàng ngay trong tài khoản</li>
        </ul>
        <RouterLink class="market-primary-action mt-6 px-5" to="/products">
          Khám phá sản phẩm <ArrowRightIcon class="size-5" />
        </RouterLink>
      </div>

      <nav class="market-curated-hero__categories" aria-label="Ngành hàng nổi bật">
        <RouterLink v-for="entry in categoryEntries" :key="entry" to="/products">
          {{ entry }} <ArrowRightIcon class="size-4" />
        </RouterLink>
      </nav>
    </div>
  </section>
</template>
