# Sprint 04 — Inventory & Availability

## Quyết định đã chốt

1. Dùng `StockEntry`/`StockEntryItem` với trạng thái draft → confirmed; không ghi nhập kho trực
   tiếp vào ledger.
2. Dùng đồng thời `InventoryBalance.reserved_stock` và `StockReservation`; mỗi thao tác
   reserve/release/commit cập nhật cả hai trong một transaction.
3. BON-09 waitlist nằm trong scope và đã triển khai.
4. `ADJUSTMENT.quantity` là số tồn thực tế mới; ledger lưu delta đã tính dưới row lock.
5. Các hàm reservation nhận actor bắt buộc vì `StockMovement.created_by` không nullable.

## Definition of Done

- [x] Models, DB constraints, indexes, migration và backfill `stock_quantity`.
- [x] Ledger append-only có bucket và balance-after.
- [x] StockService duy nhất, `transaction.atomic()`, `select_for_update()`, `F()`.
- [x] Workflow phiếu nhập, xuất, kiểm kê; chặn âm tồn và confirm/sửa trùng.
- [x] Reservation idempotent theo `(variant, order_reference)`.
- [x] Low-stock notification và customer waitlist/restock notification.
- [x] Seller API scope theo shop từ authenticated user; permission tests Seller A/B.
- [x] Frontend feature-based với API/store/forms/views và product waitlist.
- [x] Unit/API/component/store tests; test concurrent dành cho PostgreSQL.
- [x] README, API design, database design, ERD và OpenAPI được cập nhật.

## Validation

Các lệnh bàn giao:

```bash
cd ecommerce/backend
pytest apps/inventory --cov=apps.inventory --cov-report=term-missing
ruff check .
python manage.py makemigrations --check --dry-run

cd ../frontend
npm test
npm run lint
npm run build
```

SQLite smoke test không thể kiểm tra row lock và sẽ skip concurrency case. CI/PostgreSQL phải chạy
case này trước khi merge.
