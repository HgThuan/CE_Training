<script setup lang="ts">
defineProps<{
  kind: 'terms' | 'privacy'
}>()
</script>

<template>
  <main class="mx-auto min-h-screen max-w-3xl px-5 py-12 sm:py-16">
    <RouterLink
      class="text-sm font-semibold text-indigo-600 hover:text-indigo-500"
      to="/auth/register"
    >
      ← Quay lại đăng ký
    </RouterLink>
    <article class="mt-8 rounded-2xl bg-white p-6 shadow-sm ring-1 ring-gray-200 sm:p-10">
      <template v-if="kind === 'terms'">
        <h1 class="text-3xl font-bold tracking-tight text-gray-950">Điều khoản sử dụng</h1>
        <p class="mt-4 leading-7 text-gray-600">
          Khi tạo tài khoản, bạn cam kết cung cấp thông tin chính xác, bảo vệ thông tin đăng nhập và
          sử dụng nền tảng đúng mục đích.
        </p>
        <h2 class="mt-8 text-xl font-semibold text-gray-900">Tài khoản và giao dịch</h2>
        <p class="mt-3 leading-7 text-gray-600">
          Bạn chịu trách nhiệm với hoạt động phát sinh từ tài khoản của mình. Mọi đơn hàng và yêu
          cầu hỗ trợ được xử lý theo thông tin hiển thị tại thời điểm giao dịch.
        </p>
      </template>
      <template v-else>
        <h1 class="text-3xl font-bold tracking-tight text-gray-950">Chính sách bảo mật</h1>
        <p class="mt-4 leading-7 text-gray-600">
          Chúng tôi chỉ thu thập thông tin cần thiết để tạo tài khoản, xử lý đơn hàng và hỗ trợ bạn
          trong quá trình sử dụng dịch vụ.
        </p>
        <h2 class="mt-8 text-xl font-semibold text-gray-900">Cách sử dụng thông tin</h2>
        <p class="mt-3 leading-7 text-gray-600">
          Thông tin cá nhân được bảo vệ và chỉ được sử dụng cho việc vận hành dịch vụ, phòng chống
          gian lận và thực hiện nghĩa vụ pháp lý.
        </p>
      </template>
      <p class="mt-8 text-sm text-gray-500">
        Đây là nội dung cơ bản cho môi trường phát triển nội bộ và cần được bộ phận pháp lý phê
        duyệt trước khi phát hành chính thức.
      </p>
    </article>
  </main>
</template>
