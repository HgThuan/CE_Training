# Coding Standards

Tài liệu này là quy chuẩn viết code hằng ngày, cụ thể hóa các nguyên tắc ở `PROJECT_CONSTITUTION.md`. Khi có xung đột, `PROJECT_CONSTITUTION.md` là nguồn thẩm quyền cao nhất.

## 1. Nguyên tắc chung khi viết code

- **Readability first**: tên biến/hàm rõ nghĩa, không viết tắt khó hiểu; không giảm số dòng bằng cách hy sinh sự rõ ràng.
- **Business logic không nằm trong View, Serializer, Model** (Backend) hay trong component trang (Frontend) — luôn đặt ở Service Layer / composable.
- **DRY**: logic lặp lại ≥ 2 lần → tách thành helper/utility/service/base class.
- **KISS**: không dùng design pattern nếu không thật sự cần.
- Áp dụng SOLID khi phù hợp, đặc biệt Single Responsibility, Open-Closed, Dependency Inversion.

## 2. Naming Convention

| Loại | Convention | Ví dụ |
|---|---|---|
| Class (chung) | PascalCase | `ProductService` |
| Model (Django) | PascalCase, số ít | `Product` |
| Serializer | PascalCase + hậu tố `Serializer` | `ProductSerializer` |
| Permission | PascalCase, tiền tố `Is` | `IsSeller` |
| Celery Task | PascalCase + hậu tố `Task` | `GenerateEmbeddingTask` |
| Biến, hàm (Python) | snake_case | `calculate_total_price()` |
| Biến, hàm (TypeScript) | camelCase | `calculateTotalPrice()` |
| Component Vue | PascalCase | `ProductCard.vue` |
| Composable Vue | camelCase, tiền tố `use` | `useCart.ts` |
| Route API | kebab-case, danh từ số nhiều | `/products`, `/order-items` |
| Bảng DB (soft delete) | luôn có cặp `is_deleted` + `deleted_at` | — |

## 3. API Design

RESTful, đặt tên theo tài nguyên (danh từ), không theo hành động:

```
GET    /products              # danh sách
POST   /products               # tạo mới
GET    /products/{id}           # chi tiết
PATCH  /products/{id}            # cập nhật một phần
DELETE /products/{id}             # xóa (thường là soft delete)
```

Sai — không dùng dạng RPC-style:
```
GET  /getProducts
POST /updateProduct
```

Version hóa API: `/api/v1/...`. Mọi endpoint list đều hỗ trợ phân trang (`PageNumberPagination` hoặc tương đương).

## 4. Response Format

Tất cả API trả về cùng cấu trúc.

**Thành công:**
```json
{
    "success": true,
    "message": "Lấy danh sách sản phẩm thành công",
    "data": { }
}
```

**Lỗi:**
```json
{
    "success": false,
    "message": "Dữ liệu không hợp lệ",
    "errors": {
        "price": ["Giá phải lớn hơn 0"]
    }
}
```

**Danh sách phân trang** (bắt buộc cho mọi API list):
```json
{
    "success": true,
    "message": "...",
    "data": [ ],
    "meta": {
        "page": 1,
        "page_size": 20,
        "total_items": 134,
        "total_pages": 7
    }
}
```

## 5. Error Handling

Không để Exception thô lộ ra response. Phân loại rõ ràng và xử lý qua exception handler chung của DRF:

| Loại lỗi | HTTP Status gợi ý |
|---|---|
| Validation Error | 400 |
| Authentication Error | 401 |
| Permission Error | 403 |
| Not Found | 404 |
| Business Error (vd: hết hàng, voucher hết hạn) | 400 hoặc 409 |
| System Error | 500 (không lộ chi tiết ở production) |

Ở production, không trả traceback hay thông tin nội bộ trong `message`/`errors`.

## 6. Database Conventions

- Mọi bảng có `created_at`, `updated_at`.
- Soft delete: dùng đồng thời `is_deleted` (bool, có index) + `deleted_at` (datetime) — không trộn lẫn quy ước giữa các module.
- Tiền tệ: luôn `DecimalField`, không dùng `Float`.
- Thời gian: lưu UTC trong DB (`USE_TZ = True`), convert giờ VN (UTC+7) ở tầng hiển thị.
- Ưu tiên Foreign Key thay vì lưu ID thủ công; index cho `email`, `slug`, `status`, `created_at`.
- Số dư/tồn kho không bao giờ set trực tiếp — đi qua service duy nhất + bản ghi giao dịch append-only (xem `ARCHITECTURE.md` mục 7).

## 7. Concurrency

- Thao tác thay đổi tồn kho/số dư: bắt buộc `transaction.atomic()` + `select_for_update()` hoặc `F()` expression.
- Không đọc-tính toán-ghi đè (read-modify-write) không khóa.
- `CheckConstraint` ở tầng DB đảm bảo giá trị không âm.

## 8. Authentication & Authorization

- JWT (access ngắn hạn + refresh, có rotation & blacklist khi logout).
- Không hard-code role trong code — role lấy từ claim JWT / DB.
- Mọi endpoint khai báo permission rõ ràng; permission object-level cho dữ liệu thuộc về một shop/khách hàng cụ thể.
- Seller/Customer chỉ thao tác dữ liệu của chính mình — queryset luôn scope theo `request.user`, không tin ID từ client (xem `ARCHITECTURE.md` mục 8).

## 9. Frontend Standards

- TypeScript strict mode; tránh `any` (nếu buộc dùng, phải có comment giải thích).
- Không gọi `axios` trực tiếp trong component — qua `api.ts` của feature.
- State dùng chung qua Pinia store, không prop-drilling nhiều tầng.
- ESLint + Prettier phải pass trước khi merge.
- Cấu trúc thư mục theo domain (`features/`), xem chi tiết `ARCHITECTURE.md` mục 3.

## 10. Performance

- Luôn dùng `select_related()` / `prefetch_related()` khi query có quan hệ FK/M2M — tránh N+1 query.
- Cache Redis cho dữ liệu đọc nhiều (trang chủ, cây danh mục, chi tiết sản phẩm, kết quả AI) kèm chiến lược invalidate rõ ràng.
- Tác vụ chậm (gửi email, sinh nội dung AI, re-index embeddings, xuất Excel, thống kê định kỳ) đưa vào Celery, không chạy đồng bộ trong request.

## 11. Logging

- Không dùng `print()` — dùng `logging` hoặc `loguru`.
- Log có cấu trúc, gắn `request_id`, `user_id`.
- Log riêng cho lỗi thanh toán và lỗi gọi AI provider.

## 12. Security

- Không commit `.env`, secret key, API key, mật khẩu DB.
- Toàn bộ secrets qua biến môi trường; có `.env.example` liệt kê đầy đủ biến cần thiết (không chứa giá trị thật).
- Chống SQL injection (dùng ORM, không raw SQL nối chuỗi), XSS (sanitize rich-text bằng `bleach`/`nh3`), CSRF.
- Rate limit các endpoint nhạy cảm (đăng nhập, OTP, reset mật khẩu).
- Validate & giới hạn upload file (loại, dung lượng, kiểm tra content-type thật).
- Webhook/callback thanh toán phải idempotent (xem `PROJECT_CONSTITUTION.md` mục 15).

## 13. Git Convention

**Branch:**
```
main
develop
feature/<ten-tinh-nang>
hotfix/<ten-loi>
```

**Commit message** (Conventional Commits):
```
feat:     thêm tính năng mới
fix:      sửa lỗi
refactor: tái cấu trúc, không đổi hành vi
docs:     thay đổi tài liệu
test:     thêm/sửa test
style:    format code, không đổi logic
chore:    việc vặt (cập nhật dependency, config...)
```

Ví dụ: `feat: thêm API tạo Flash Sale (ADM-19)`

Mọi PR tự review trước khi xin review từ người khác. Không merge khi CI (lint + test) fail.

## 14. Testing

- Mỗi chức năng quan trọng: Unit Test + API Test + Permission Test.
- **Độ phủ tối thiểu 60%** cho module core: giỏ hàng, checkout, voucher, tồn kho.
- Bắt buộc có test case mô phỏng concurrent request chống oversell tồn kho.
- Backend: `pytest` + `pytest-django` + `factory_boy`. Frontend: `vitest` + `@vue/test-utils`.
- Không merge khi test thất bại.

## 15. Documentation

Mỗi module cần có README, API doc (tự sinh qua `drf-spectacular`), và Database design liên quan. Cập nhật tài liệu ngay khi thêm/đổi tính năng — không để tài liệu lệch với code.

## 16. Quy tắc khi AI hỗ trợ sinh code

- Giải thích trước khi viết, giải thích sau khi viết — không bỏ qua bước phân tích.
- Không viết toàn bộ logic trong View/component trang.
- Tuân thủ kiến trúc đã định nghĩa ở `ARCHITECTURE.md`.
- Nếu có nhiều phương án khả thi, so sánh ưu/nhược điểm trước khi chọn, và nêu rõ lý do.
- Chủ động đề xuất cải tiến nếu phát hiện thiết kế hiện tại chưa hợp lý.

## 17. Definition of Done

Một task chỉ hoàn thành khi:
- [ ] Đã phân tích yêu cầu
- [ ] Đã thiết kế database (nếu có)
- [ ] Đã thiết kế API (nếu có)
- [ ] Đã triển khai mã nguồn
- [ ] Đã giải thích mã nguồn
- [ ] Đã kiểm thử (đạt độ phủ yêu cầu với module core)
- [ ] Đã xử lý các trường hợp lỗi
- [ ] Đã cập nhật tài liệu liên quan

## 18. Tài liệu liên quan

- `PROJECT_CONSTITUTION.md` — nguyên tắc nền tảng, chi tiết đầy đủ hơn cho từng mục ở trên.
- `ARCHITECTURE.md` — kiến trúc tổng thể mà các quy chuẩn này phục vụ.
- `TECH_STACK.md` — công nghệ cụ thể được áp dụng các quy chuẩn này.
- `PROJECT_OVERVIEW.md` — bối cảnh nghiệp vụ của dự án.
