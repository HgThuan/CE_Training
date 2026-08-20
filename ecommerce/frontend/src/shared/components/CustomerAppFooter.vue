<script setup lang="ts">
import { ArrowRightIcon, ChatBubbleLeftRightIcon, ShieldCheckIcon } from '@heroicons/vue/24/outline'
</script>

<template>
  <footer class="market-footer">
    <div class="market-footer__inner">
      <div class="market-footer__intro">
        <RouterLink class="market-footer__wordmark" to="/">Mercato</RouterLink>
        <p>Mua sắm rõ ràng, hỗ trợ đúng lúc và kết nối trực tiếp với gian hàng bạn tin chọn.</p>
      </div>

      <nav class="market-footer__links" aria-label="Liên kết mua sắm">
        <p>Khám phá</p>
        <RouterLink to="/products">Tất cả sản phẩm</RouterLink>
        <RouterLink to="/voucher-center">Kho voucher</RouterLink>
        <RouterLink to="/flash-sales">Flash sale</RouterLink>
      </nav>

      <nav class="market-footer__links" aria-label="Hỗ trợ khách hàng">
        <p>Hỗ trợ</p>
        <RouterLink to="/account/orders">Theo dõi đơn hàng</RouterLink>
        <RouterLink to="/account/chat">Nhắn tin gian hàng</RouterLink>
        <RouterLink to="/account/profile">Tài khoản của tôi</RouterLink>
      </nav>

      <div class="market-footer__assurance">
        <p><ShieldCheckIcon class="h-5 w-5" /> Thanh toán và dữ liệu được bảo vệ</p>
        <RouterLink to="/products">
          Bắt đầu mua sắm <ArrowRightIcon class="h-4 w-4" aria-hidden="true" />
        </RouterLink>
        <span><ChatBubbleLeftRightIcon class="h-4 w-4" /> Trợ lý mua sắm luôn sẵn sàng</span>
      </div>
    </div>
    <div class="market-footer__legal">© {{ new Date().getFullYear() }} Mercato · Sàn thương mại điện tử đa gian hàng</div>
  </footer>
</template>
