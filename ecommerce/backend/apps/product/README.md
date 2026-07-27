# Product app — schema and business foundation

Ứng dụng `product` cung cấp schema, state machine, service layer, selector và HTTP API cho Product
Management của Sprint 3. Frontend quản trị sản phẩm sẽ được nối ở phase tiếp theo.

## Models

- `Product`: thuộc Shop, Category và Brand; trạng thái duyệt, rating/sold counters, price cache
  và soft delete.
- `ProductMedia`: ảnh/video theo Product hoặc Variant, partial unique cho media primary.
- `Attribute`, `AttributeValue`: thuộc tính toàn sàn hoặc theo Shop.
- `ProductAttributeValue`: tập giá trị thuộc tính được phép dùng cho Product.
- `ProductVariant`: SKU/barcode theo Shop, giá VNĐ, trạng thái và soft delete.
- `VariantAttributeValue`: mỗi Variant chỉ có một giá trị cho mỗi Attribute.

Tất cả primary key dùng UUID. Các bảng mutable dùng `TimeStampedModel`. Tiền dùng
`DecimalField(max_digits=18, decimal_places=0)`.

## Business layer

- Slug Product unique trong một Shop khi Product chưa bị soft-delete.
- Category được bảo vệ bằng `on_delete=PROTECT`; Brand dùng `SET_NULL`.
- Price cache, rating, Variant price/weight được bảo vệ bằng database check constraints.
- Thuộc tính global (`shop=NULL`) và thuộc tính theo Shop có unique constraints riêng.
- `ProductService` tạo/cập nhật/soft-delete/submit/approve/reject/hide và cập nhật price cache.
- `ProductStateMachine` là điểm đổi status duy nhất, thực thi transition tại
  `BASIC_DESIGN.md` §14.1 và ghi structured `AuditLog`.
- `MediaService` xác minh ảnh bằng Pillow, video bằng MP4/WebM magic bytes; giới hạn 9 ảnh + 1
  video và lưu qua Django Storage. Dung lượng cấu hình qua `MAX_IMAGE_UPLOAD_MB` và
  `MAX_VIDEO_UPLOAD_MB`.
- `VariantService` tạo tích Descartes từ AttributeValue, tự sinh SKU, kiểm tra SKU/barcode theo
  Shop và đảm bảo `product.shop_id == variant.shop_id`.
- `ProductSelector` cung cấp query public, Seller, pending Admin, toàn bộ Admin và detail đã
  eager-load relations.

Mọi write path Seller khóa row theo đồng thời primary key và Shop suy ra từ authenticated user.
Không dùng `shop_id` trong request body hoặc object truyền vào làm căn cứ ownership.

## API

- Seller CRUD: `/api/v1/seller/products/`, detail theo UUID và action submit.
- Seller media/variant: nested dưới `/api/v1/seller/products/{id}/`; thuộc tính khả dụng tại
  `/api/v1/seller/attributes/`.
- Admin moderation: pending/approve/reject/hide/soft-delete dưới `/api/v1/admin/products/`.
- Public: `/api/v1/products/` và `/api/v1/products/{slug}/`.

List endpoint dùng pagination chuẩn, filter serializer và selector riêng. Public product slug chỉ
unique trong phạm vi Shop; khi nhiều Shop có cùng slug, detail endpoint yêu cầu query
`shop_slug` để không chọn nhầm tenant.

## Migration

Migration khởi tạo: `product.0001_initial`, phụ thuộc `account.0004` và `catalog.0001`.
`common.0003_alter_auditlog_target_id` đổi audit target sang chuỗi để lưu được UUID Product mà
vẫn tương thích ID số của Account/Shop.

```bash
python manage.py makemigrations product
python manage.py migrate
```

## Tests

```bash
DJANGO_SETTINGS_MODULE=config.settings.test TEST_USE_SQLITE=true \
  .venv/bin/pytest apps/product/tests
```

Checkpoint hiện tại: 63 Product tests (21 model/constraint, 26 service/state/selector và 16 API/
permission/query-optimization) pass.
