# Catalog app

Ứng dụng `catalog` triển khai ADM-15 và ADM-16 cho Category/Brand.

## Kiến trúc

- `models.py`: `Category`, `Brand` với UUID, timestamp, trạng thái và soft delete.
- `services.py`: toàn bộ write/business rule, sinh slug, chống cycle, reorder transaction.
- `selectors.py`: query public/admin; cây public được dựng từ một query phẳng.
- `serializers.py`: validation request và response schema.
- `views.py`: điều phối request → service/selector → response chuẩn.

`TimeStampedModel` dùng chung nằm tại `apps.common.models`; Catalog không phụ thuộc ngược vào
domain Account. Category dùng self-FK `RESTRICT`. API và Django Admin không hard-delete; khi
Product được triển khai, FK `Product.category` phải tiếp tục dùng `RESTRICT`.

## API

- Public: `GET /api/v1/categories/`, `GET /api/v1/brands/`.
- Admin Category: list/create/detail/update/soft-delete và reorder dưới
  `/api/v1/admin/categories/`.
- Admin Brand: list/create/detail/update/soft-delete dưới `/api/v1/admin/brands/`.

List Brand và các list Admin dùng `StandardPagination`. Category public trả toàn bộ cây nên không
phân trang.

## Kiểm thử

```bash
DJANGO_SETTINGS_MODULE=config.settings.test TEST_USE_SQLITE=true \
  .venv/bin/pytest apps/catalog/tests
```
