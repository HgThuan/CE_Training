# Payment (Sprint 07)

Payment nằm ở cấp `Order`, không nằm ở `ShopOrder`: một checkout nhiều shop chỉ redirect và nhận callback cho một giao dịch VNPay bằng `Order.grand_total`. `Order.payment_status` là nguồn sự thật duy nhất cho online payment. Seller chỉ được confirm shop order VNPay sau khi aggregate đã `PAID`.

`PaymentProvider` tách provider khỏi service. Sprint này có COD và VNPay sandbox. Callback VNPay:

1. verify HMAC SHA-512;
2. lock Payment + Order;
3. verify transaction ref, amount và currency;
4. dùng `provider_event_id` để chống callback lặp;
5. append `PaymentTransaction`, rồi mới cập nhật Payment/Order.

Refund một shop dùng bảng `refunds` với cả `payment_id` và `shop_order_id`, cho phép hoàn một phần từ payment aggregate. Provider refund được xử lý retryable ngoài transaction hủy đơn.
