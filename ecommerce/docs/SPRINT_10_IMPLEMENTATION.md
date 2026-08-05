# Sprint 10 — Dashboard, Reports & Administration

Phạm vi triển khai: ADM-01..03, ADM-12, ADM-22..26, SEL-01, NFR-06, NFR-15 và NFR-16.
BON-11, BON-13 và AI-14 không thuộc đợt triển khai này.

## Chức năng

- Dashboard Admin: tổng doanh thu, đơn hàng, khách hàng mới, sản phẩm mới, biểu đồ theo ngày và top sản phẩm.
- Dashboard Seller: cùng bộ số liệu nhưng luôn giới hạn theo shop của tài khoản đăng nhập.
- Báo cáo: top seller, khách hàng, danh mục; tỷ lệ hủy và trả; xuất XLSX/PDF.
- Theo dõi doanh thu từng seller cho Admin.
- Audit Log có filter theo hành động, loại đối tượng và request ID.
- SiteSetting dạng key-value, tự xác định kiểu dữ liệu, cache 5 phút và xóa cache khi cập nhật.
- Dashboard cache 5 phút theo người dùng và khoảng thời gian.
- Structured JSON log gồm request ID, user ID, path, method, status và thời gian xử lý.
- Backup PostgreSQL dạng custom format, manifest SHA-256, kiểm tra catalog và restore vào database tách biệt.

## API

Các endpoint nằm dưới `/api/v1/` và yêu cầu JWT:

- `GET admin/dashboard/summary|revenue-chart|top-products/`
- `GET admin/shops/{id}/revenue/`
- `GET admin/reports/top-sellers|top-customers|top-categories|cancel-return-rate/`
- `POST admin/reports/export/` với `report` và `format` (`xlsx` hoặc `pdf`)
- `GET admin/audit-logs/`
- `GET|PUT admin/settings/`
- `GET seller/dashboard/summary|revenue-chart|top-products/`

## Backup và khôi phục

```bash
python manage.py backup_database
python manage.py verify_backup mercato-YYYYMMDDTHHMMSSZ.dump
python manage.py restore_database mercato-YYYYMMDDTHHMMSSZ.dump \
  --database mercato_restore_test --confirm mercato_restore_test
```

`restore_database` từ chối database đang cấu hình trong ứng dụng và yêu cầu xác nhận chính xác tên database đích. Sau restore, chạy smoke test/migration check trên database tách biệt trước khi phê duyệt quy trình phục hồi production.

## Kiểm thử

- Backend: quyền Admin/Seller, scope dashboard Seller, SiteSetting + cache/audit và định dạng XLSX/PDF.
- Frontend: lint, type-check/build và toàn bộ Vitest hiện có.
