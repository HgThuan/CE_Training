# Inventory app — Sprint 04

`apps.inventory` triển khai SEL-06 đến SEL-09 và BON-09. Mọi request Seller được scope bằng
`request.user.shop`; API không nhận `shop_id` từ client.

## Quyết định thiết kế

- `StockEntry`/`StockEntryItem` là phiếu nhập hai trạng thái. Chỉ action `confirm` cộng tồn; phiếu
  đã xác nhận không thể sửa và muốn đảo phải lập chứng từ bù.
- `StockOutEntry` dùng `OUT` hoặc `ADJUSTMENT`. Với `ADJUSTMENT`, item lưu số tồn thực tế mới
  (cho phép 0), còn ledger lưu delta so với số dư đang khóa.
- `InventoryBalance` có hai counter đọc nhanh: `available_stock` và `reserved_stock`.
  `StockReservation` giữ chi tiết theo `(variant, order_reference)` để retry checkout idempotent.
- `StockMovement.bucket` tách `AVAILABLE`/`RESERVED`; vì vậy `balance_after` luôn có một nghĩa duy
  nhất và reserve/release tạo hai movement tương ứng.
- `StockMovement` là append-only ở model và không được đăng ký writable trong admin.
- `reserve_stock`, `release_stock`, `commit_stock` nhận `user` bắt buộc để mọi movement có người
  thao tác đúng với SEL-08.

`StockService` là service duy nhất cập nhật counter hoặc tạo movement. Các write path dùng
`transaction.atomic()`, khóa balance theo thứ tự `variant_id`, cập nhật bằng `F()` và đọc lại số
dư trong transaction trước khi ghi ledger.

## API

| Method | Endpoint | Mục đích |
|---|---|---|
| GET | `/api/v1/seller/inventory/` | Tồn kho; `low_stock=true` lọc SKU chạm ngưỡng |
| GET | `/api/v1/seller/inventory/movements/` | Sổ kho; lọc variant và khoảng thời gian |
| GET/POST | `/api/v1/seller/inventory/stock-entries/` | Danh sách/tạo phiếu nhập |
| PATCH | `/api/v1/seller/inventory/stock-entries/{id}/` | Sửa phiếu nhập draft |
| POST | `/api/v1/seller/inventory/stock-entries/{id}/confirm/` | Xác nhận và cộng tồn |
| GET/POST | `/api/v1/seller/inventory/stock-out-entries/` | Danh sách/tạo phiếu xuất/kiểm kê |
| PATCH | `/api/v1/seller/inventory/stock-out-entries/{id}/` | Sửa phiếu draft |
| POST | `/api/v1/seller/inventory/stock-out-entries/{id}/confirm/` | Xác nhận phiếu |
| POST | `/api/v1/seller/inventory/{variant_id}/threshold/` | Cập nhật ngưỡng tồn thấp |
| POST | `/api/v1/customer/products/{variant_id}/waitlist/` | Đăng ký báo khi có hàng |

List response dùng `success/message/data/meta`; mọi lỗi đi qua exception handler chung.

## Migration và dữ liệu demo

Migration `inventory.0001_initial` tạo constraints/index và backfill balance từ field
`ProductVariant.stock_quantity` cũ. Command có thể chạy lại an toàn cho các row thiếu:

```bash
python manage.py backfill_inventory_balance
python manage.py seed_inventory_demo --quantity 20 --unit-cost 50000
```

Field cũ chỉ còn compatibility fallback và không được cập nhật bởi Product API.

## Kiểm thử

```bash
pytest apps/inventory --cov=apps.inventory --cov-report=term-missing
```

Concurrency test dùng transaction thật và chỉ chạy khi database hỗ trợ `SELECT FOR UPDATE`
(PostgreSQL). SQLite được dùng cho smoke test local nhưng chủ động skip case row-lock.
