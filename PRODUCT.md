# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Khách hàng Việt Nam mua điện tử, thời trang và hàng tiêu dùng trên desktop lẫn mobile. Họ cần tìm sản phẩm nhanh, so sánh lựa chọn, săn khuyến mại và hoàn tất thanh toán với thông tin rõ ràng, đáng tin cậy.

Các actor khác của hệ thống gồm Seller và Admin, nhưng visual identity được thay mới trong lần này chỉ áp dụng cho trải nghiệm Customer và storefront công khai.

## Product Purpose

Mercato là sàn thương mại điện tử đa nhà bán, hỗ trợ khách hàng khám phá, đánh giá, mua và theo dõi sản phẩm từ nhiều gian hàng trong một hành trình thống nhất. Thành công nghĩa là khách tìm đúng sản phẩm nhanh, hiểu đúng giá và trạng thái hàng hóa, tự tin đặt hàng và có thể quay lại quản lý toàn bộ hoạt động mua sắm.

## Positioning

Mercato kết hợp catalog đa nhà bán với tìm kiếm ngôn ngữ tự nhiên, semantic search, gợi ý sản phẩm, tóm tắt nội dung và hỗ trợ AI trong chính luồng mua sắm; AI không được làm gián đoạn luồng thương mại cốt lõi khi provider lỗi.

## Operating Context

- Khách duyệt danh mục, tìm kiếm hoặc dùng AI để khám phá sản phẩm.
- Khách so sánh, lưu yêu thích, xem gian hàng, đánh giá, hỏi đáp và chọn biến thể.
- Giỏ hàng có thể chứa sản phẩm từ nhiều shop; voucher sàn và voucher shop có phạm vi riêng.
- Checkout hỗ trợ COD và cổng thanh toán sandbox, kèm địa chỉ và vận chuyển.
- Sau mua, khách theo dõi đơn, chat, nhận thông báo, đánh giá và thực hiện yêu cầu hậu mãi khi đủ điều kiện.
- Giao diện và nội dung chính sử dụng tiếng Việt, định dạng tiền VND và ngày theo quy ước Việt Nam.

## Capabilities and Constraints

- Giữ nguyên Vue 3 SPA, TypeScript, Tailwind CSS, Pinia, Vue Router và REST/WebSocket contracts hiện có.
- Giữ nguyên route, route name, API, store, composable, phân quyền và business logic.
- Customer UI phải hoạt động từ 320px đến desktop rộng, hỗ trợ chuột, bàn phím và touch.
- Các trạng thái loading, empty, error, success, disabled, thiếu ảnh và nội dung dài phải là một phần chính thức của hệ thống.
- Giá gốc chỉ được gạch khi lớn hơn giá bán; mọi trạng thái CTA mua hàng phải giải thích được.
- Không phát minh giá, đánh giá, lượng bán, khuyến mại, bằng chứng thương mại hoặc chính sách chưa có trong dữ liệu.
- Route guard chỉ phục vụ UX; quyền vẫn do backend kiểm tra.

## Brand Commitments

- Giữ tên sản phẩm “Mercato”.
- Không có logo, màu sắc hay visual identity hiện tại nào bắt buộc phải giữ.
- Được phép thay toàn bộ visual identity Customer; Admin và Seller nằm ngoài phạm vi thay đổi.
- Giọng điệu: rõ ràng, trực tiếp, hữu ích và đáng tin cậy; tránh hype không có bằng chứng.

## Evidence on Hand

- Đặc tả và kiến trúc trong `ecommerce/docs/`.
- Kế hoạch audit Customer tại `ecommerce/docs/KE_HOACH_SUA_UI_CUSTOMER.md`.
- Component, test, API types và nghiệp vụ đang chạy trong `ecommerce/frontend/src/`.
- Dữ liệu sản phẩm, banner và hình ảnh thật đến từ API; hiện chưa có bộ asset thương hiệu Customer mới được phê duyệt.

## Product Principles

1. Giá, tồn kho, khuyến mại và tổng thanh toán phải luôn dễ hiểu và không gây hiểu nhầm.
2. Tìm kiếm và khám phá nhanh nhưng không lấn át hành trình mua hàng quen thuộc.
3. Một ngôn ngữ giao diện duy nhất xuyên suốt storefront, checkout và account.
4. AI tăng chất lượng quyết định; lỗi AI không được chặn tác vụ thương mại.
5. Mobile là trải nghiệm đầy đủ, không phải bản desktop bị thu nhỏ.

## Accessibility & Inclusion

- Mục tiêu WCAG 2.2 AA cho tương phản, focus, điều khiển bàn phím và tên truy cập.
- Vùng chạm tối thiểu 44×44px cho điều khiển quan trọng.
- Không truyền đạt trạng thái chỉ bằng màu sắc.
- Hỗ trợ giảm chuyển động theo `prefers-reduced-motion`.
