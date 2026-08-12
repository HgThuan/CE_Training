# Order / Checkout (Sprint 07)

Một lần checkout tạo đúng một `Order`, sau đó tách thành một `ShopOrder` cho mỗi shop. Seller chỉ truy vấn `ShopOrder` của shop lấy từ user đăng nhập; không nhận `shop_id` từ client.

## Inventory lifecycle

| Sự kiện | Bucket tồn kho | Service |
|---|---|---|
| Checkout | available → reserved | `StockService.reserve_stock` |
| Seller confirm | reserved bị tiêu thụ | `StockService.commit_stock` |
| Hủy trước confirm / payment hết hạn | reserved → available | `StockService.release_stock` |
| Seller hủy sau confirm | cộng lại available và ghi ledger adjustment | `StockService.adjust_stock` |

Mọi bước chạy trong transaction, có row lock và reference ổn định là `shop_order_code`. `OrderCancellation.stock_restored_at` và `voucher_released_at` ngăn side effect chạy hai lần.

COD không dùng `Order.payment_status` để biểu diễn tiền đã thu theo từng shop. Khi fulfillment tới `DELIVERED`, `ShopOrder.cod_collected_at` được set; `Order.payment_status` giữ `PENDING`.

## State machine

`PENDING_CONFIRMATION → CONFIRMED → PACKING → SHIPPING → DELIVERED → COMPLETED`. Customer chỉ hủy khi còn pending; Seller được hủy trước khi shipping, gồm cả `CONFIRMED → CANCELLED` theo quyết định Sprint 07.

Checkout yêu cầu header `Idempotency-Key`; retry cùng key trả lại đúng aggregate cũ và không reserve kho lần hai.
