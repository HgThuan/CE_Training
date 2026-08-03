# Sprint 07 — Checkout, Payment & Order Lifecycle

## Quyết định đã triển khai

- Một `Order` cho toàn checkout, nhiều `ShopOrder`; Payment/PaymentTransaction gắn `Order`.
- COD giữ `Order.payment_status=PENDING`; thu tiền được snapshot ở `ShopOrder.cod_collected_at`.
- Reserve lúc checkout, commit lúc Seller confirm, release nếu hủy trước confirm, ledger adjustment nếu hủy sau confirm.
- Hủy theo từng `ShopOrder`; `CONFIRMED → CANCELLED` được phép cho Seller.
- VNPay sandbox là online provider; callback verify chữ ký, amount/currency và idempotent theo provider event.
- Tối đa một voucher platform và một voucher shop trên mỗi shop order.
- Shipping dùng flat fee theo shop và optional free-shipping threshold, không tích hợp carrier/BON-01.
- Checkout idempotency lưu ở `orders.idempotency_key`; payment attempt có key riêng.

## API/UI

Các endpoint giữ đúng contract `/checkout/*`, `/orders/*`, `/seller/orders/*`, `/admin/orders/*`, `/payment/*`. Frontend có checkout, return verification, Customer order timeline, Seller lifecycle/packing slip và Admin filters.
