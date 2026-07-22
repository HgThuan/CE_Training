# Architecture

Tài liệu này mô tả kiến trúc kỹ thuật của hệ thống. Các nguyên tắc thiết kế nền tảng (SOLID, DRY, KISS...) nằm ở `PROJECT_CONSTITUTION.md`; tài liệu này tập trung vào **cấu trúc thực tế** của hệ thống.

## 1. Kiến trúc tổng thể

Hệ thống theo kiến trúc phân lớp (layered architecture):

```
Presentation Layer      ← Vue 3 components, Django Views/Serializers
      ↓
Application Layer       ← Service Layer (business logic)
      ↓
Domain Layer             ← Models, business rules
      ↓
Infrastructure Layer     ← Database, Redis, Celery, AI Providers, Payment Gateway
```

Nguyên tắc: mỗi lớp chỉ phụ thuộc vào lớp bên dưới, không phụ thuộc ngược. Business logic không bao giờ nằm ở Presentation Layer (View/Serializer/Component).

## 2. Kiến trúc Backend

Mỗi module nghiệp vụ là một Django app độc lập, cấu trúc thống nhất:

```
apps/
  product/
    models.py         # Domain model
    serializers.py     # Presentation — validate & format dữ liệu vào/ra
    views.py            # Presentation — nhận request, gọi service, trả response
    urls.py
    services.py         # Application — business logic chính
    repositories.py     # Infrastructure — truy vấn DB phức tạp, tách khỏi ORM query rải rác
    permissions.py       # Object-level & role-level permission
    validators.py
    selectors.py          # Query đọc dữ liệu phức tạp (đối lập với services ghi dữ liệu)
    tasks.py               # Celery tasks
    signals.py
    tests/
```

Không bắt buộc dùng tất cả các file — chỉ tạo khi module thật sự cần. Ví dụ module đơn giản như `Brand` có thể chỉ cần `models.py`, `serializers.py`, `views.py`, `urls.py`.

**Luồng xử lý một request điển hình:**
```
Client → urls.py → views.py (chỉ điều phối) → services.py (business logic)
       → repositories.py / models.py (truy cập dữ liệu) → trả kết quả ngược lên
```

## 3. Kiến trúc Frontend

Tổ chức theo domain (feature-based), không theo loại file:

```
src/
  features/
    product/
      components/
      composables/
      store.ts        # Pinia store
      api.ts            # gọi axios — điểm duy nhất giao tiếp với BE của feature này
      types.ts           # type khớp với serializer BE tương ứng
    cart/
    order/
    auth/
    ...
  shared/
    components/        # component dùng chung nhiều feature
    composables/
    lib/
      http.ts            # axios instance chung + interceptor refresh token
  router/
    guards.ts            # route guard theo vai trò (Admin / Seller / Customer)
  stores/
    auth.ts
```

Quy tắc:
- Component **không** gọi axios trực tiếp — luôn qua `api.ts` của feature.
- State dùng chung giữa nhiều component đi qua Pinia store, không prop-drilling.
- Logic nghiệp vụ (tính giá, validate phức tạp) nằm ở composable/store, không viết trong component trang.
- Type ở FE (`types.ts`) phải khớp với serializer BE — cập nhật đồng thời khi API đổi.

## 4. Kiến trúc phân quyền 3 vai trò

```
User (Django auth) ──1:1── AdminProfile / SellerProfile / CustomerProfile
        │
        └── role claim trong JWT ──► DRF Permission class (BE)
                                  └► Vue Router guard (FE)
```

- Mỗi API khai báo rõ permission theo vai trò (không có endpoint "mở cho tất cả role" một cách ngầm định).
- FE dùng route guard để chặn truy cập trang không đúng vai trò — đây là UX, **không thay thế** permission check ở BE.
- Xem thêm mục 8 (Multi-tenant Data Isolation) cho object-level permission trong hệ marketplace.

## 5. Kiến trúc Realtime (WebSocket)

Dùng cho chat (SEL-16, CUS-20) và thông báo realtime (BON-08, Flash Sale realtime BON-14).

```
Client ──WebSocket (JWT auth ở handshake)──► Django Channels Consumer
                                                    │
                                                    ▼ (chỉ điều phối, không có business logic)
                                              Service Layer (lưu message, tính unread...)
                                                    │
                                                    ▼
                                              PostgreSQL (nguồn dữ liệu chính)
                                                    │
                                              Redis Channel Layer (broadcast)
```

Quy ước group name:
- Thông báo cá nhân: `user_{user_id}`
- Thông báo theo shop: `shop_{shop_id}`
- Hội thoại chat: `conversation_{conversation_id}`

Mọi message realtime đều được ghi vào DB trước/song song khi broadcast — WebSocket không phải nguồn dữ liệu duy nhất, để client reconnect vẫn lấy lại được lịch sử. Có fallback polling khi WebSocket không khả dụng.

## 6. Kiến trúc AI

```
View / Consumer
      │  (không bao giờ gọi thẳng provider)
      ▼
AIService  ──► quản lý: retry/timeout, đếm token & chi phí,
      │         log prompt/response (AIRequestLog), cache, fallback khi lỗi
      ▼
Provider interface (provider-agnostic)
      │
      ├── OpenAIProvider
      ├── ClaudeProvider
      └── GeminiProvider
```

Nguyên tắc:
- Không phụ thuộc một provider — đổi provider chỉ cần đổi implementation, không đổi code gọi ở service khác.
- Với các tác vụ phân tích số liệu (AI Sales Analytics), tính số bằng SQL trước, chỉ đưa số liệu đã tính sẵn vào prompt — không để LLM tự tính toán số.
- AIService luôn có fallback: lỗi ở AI provider không được làm sập luồng nghiệp vụ chính (ví dụ: mô tả sản phẩm vẫn hiển thị được dù tính năng tóm tắt AI đang lỗi).

Chi tiết yêu cầu bắt buộc của AIService xem `PROJECT_CONSTITUTION.md` mục 7.

## 7. Kiến trúc quản lý tồn kho / dữ liệu nhạy cảm (Data Integrity)

Rủi ro lớn nhất của hệ thống: trừ tồn kho, Flash Sale, checkout nhiều shop cùng lúc, ví điện tử, điểm thưởng — tất cả đều có khả năng xảy ra race condition khi nhiều request chạy đồng thời.

Mọi thay đổi số dư/tồn kho đi qua **một service duy nhất per domain**:

```
StockService     ──► StockMovement (append-only log)  ──► Product.stock (cập nhật qua F() / select_for_update)
WalletService     ──► WalletTransaction (append-only log) ──► Wallet.balance
PointService       ──► PointTransaction (append-only log)  ──► CustomerProfile.points
```

Không service/view nào khác được phép ghi trực tiếp vào các cột `stock`, `balance`, `points`. Toàn bộ nằm trong `transaction.atomic()` + khóa dòng. Chi tiết nguyên tắc xem `PROJECT_CONSTITUTION.md` mục 8.

## 8. Kiến trúc Multi-tenant (đa gian hàng)

```
Request (Seller đã đăng nhập)
      │
      ▼
View → Service → Repository
                     │
                     └── queryset LUÔN filter theo shop_id = request.user.seller_profile.shop_id
                          (không bao giờ lấy shop_id từ query param / request body của client)
```

Đây là lớp bảo mật riêng, tách khỏi Authorization role-based thông thường — vì lỗi ở đây (Seller A đọc được dữ liệu Seller B) là lỗ hổng phổ biến nhất của hệ marketplace. Xem thêm `PROJECT_CONSTITUTION.md` mục 14.

## 9. Kiến trúc triển khai (Deployment)

```
                     ┌─────────────┐
   Internet ───────► │    Nginx     │
                     └──────┬──────┘
                 ┌──────────┼───────────┐
                 ▼          ▼            ▼
            / → FE static   /api → BE    /ws → BE (Channels)
                            (Gunicorn)

   Backend container ──► Celery worker + Celery beat ──► Redis (broker + cache + channel layer)
                     │
                     └──► PostgreSQL (external, ngoài docker-compose, qua biến môi trường)
```

- Dockerfile FE và BE đều multi-stage (build riêng / runtime riêng).
- Mỗi service có healthcheck riêng trong `docker-compose.yml`.
- Toàn bộ cấu hình qua biến môi trường (`.env`), không hardcode trong image.

Chi tiết xem `PROJECT_CONSTITUTION.md` mục 17–18 (Docker & CI/CD).

## 10. Sơ đồ luồng dữ liệu chính (tham khảo)

**Checkout (CUS-14):**
```
Cart (nhiều shop) → Checkout → tách thành nhiều Order theo shop
    → mỗi Order: transaction.atomic()
        → select_for_update() trừ tồn kho từng item
        → validate & áp voucher (sàn + shop)
        → ghi PaymentTransaction (chờ callback nếu không phải COD)
    → OrderStatusHistory ghi trạng thái khởi tạo
```

**AI Smart Search (AI-01, AI-02):**
```
Query tự nhiên của khách → AIService (LLM trích xuất filter có cấu trúc)
    → kết hợp semantic search (pgvector, embeddings) + filter SQL (giá/danh mục)
    → trả kết quả kèm giải thích ngắn
```

## 11. Tài liệu liên quan

- `PROJECT_CONSTITUTION.md` — quy tắc bắt buộc chi tiết cho từng phần kiến trúc ở trên.
- `TECH_STACK.md` — công nghệ cụ thể dùng trong từng lớp.
- `CODING_STANDARDS.md` — quy chuẩn code khi hiện thực kiến trúc này.
- `PROJECT_OVERVIEW.md` — bối cảnh nghiệp vụ tương ứng với các sơ đồ trên.
