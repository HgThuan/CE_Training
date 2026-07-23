# Project Constitution



## 1. Project Overview

**Tên dự án:** Multi-Vendor AI E-commerce Platform

**Mục tiêu:** Xây dựng một nền tảng thương mại điện tử đa gian hàng (Multi-vendor Marketplace) có khả năng mở rộng, bảo trì và tích hợp AI nhằm nâng cao trải nghiệm mua sắm, hỗ trợ nhà bán hàng và tối ưu công tác quản trị.

Đây là đồ án tốt nghiệp nên toàn bộ mã nguồn phải được xây dựng theo tiêu chuẩn của một hệ thống thực tế.

---

## 2. Core Principles

### 2.1 Readability First
Code phải dễ đọc trước khi tối ưu. Ưu tiên:
- tên biến rõ nghĩa
- tên hàm rõ nghĩa
- cấu trúc thư mục rõ ràng

Không viết code khó hiểu chỉ để giảm số dòng.

### 2.2 Maintainability
Mọi chức năng đều phải dễ sửa đổi. Nếu một thay đổi nhỏ làm ảnh hưởng nhiều nơi thì thiết kế đó chưa tốt.

### 2.3 Scalability
Hệ thống phải có khả năng mở rộng.

Ví dụ — không viết:
```python
if payment == "vnpay":
    ...
```
Mà nên:
```
PaymentProvider
├── VNPayProvider
├── PaypalProvider
└── StripeProvider
```
để sau này chỉ cần thêm Provider mới.

### 2.4 Separation of Concerns
Mỗi module chỉ có một trách nhiệm. Không viết Business Logic trong:
- View
- Serializer
- Model

Business Logic phải nằm trong Service Layer.

### 2.5 SOLID
Áp dụng nguyên tắc SOLID khi phù hợp. Đặc biệt:
- Single Responsibility
- Open Closed
- Dependency Inversion

### 2.6 DRY
Không lặp lại code. Nếu cùng một đoạn logic xuất hiện từ hai lần trở lên thì cân nhắc tách thành:
- Helper
- Utility
- Service
- Base Class

### 2.7 KISS
Ưu tiên giải pháp đơn giản. Không sử dụng Design Pattern nếu không thật sự cần.

---

## 3. Architecture

Kiến trúc dự án theo hướng phân lớp:

```
Presentation Layer
      ↓
Application Layer
      ↓
Domain Layer
      ↓
Infrastructure Layer
```

- **Backend:** Django, Django REST Framework, PostgresSql
- **Frontend:** Vue 3, TypeScript

---

## 4. Backend Architecture

Mỗi module phải có cấu trúc tương tự:

```
apps/
  product/
    models.py
    serializers.py
    views.py
    urls.py
    services.py
    repositories.py
    permissions.py
    validators.py
    selectors.py
    tasks.py
    signals.py
    tests/
```

Không bắt buộc sử dụng tất cả. Chỉ tạo khi thật sự cần.

---

## 5. Frontend Architecture 

Frontend tổ chức theo domain (feature-based), không theo loại file, để khớp với NFR-09.

```
src/
  features/
    product/
      components/
      composables/
      store.ts        # Pinia store
      api.ts           # gọi axios, không gọi trực tiếp trong component
      types.ts          # type khớp với response BE
    cart/
    order/
    ...
  shared/
    components/       # component dùng chung, không thuộc domain nào
    composables/
    lib/
      http.ts          # axios instance chung + interceptor refresh token
  router/
    guards.ts          # route guard theo role (Admin / Seller / Customer)
  stores/
    auth.ts
```

Quy tắc bắt buộc:
- **Không gọi `axios` trực tiếp trong component.** Mọi gọi API đi qua file `api.ts` của feature tương ứng.
- **State dùng chung giữa nhiều component phải qua Pinia store**, không truyền qua props nhiều tầng (prop drilling) hay dùng biến toàn cục.
- **Type ở FE phải khớp với serializer ở BE.** Khi BE đổi response, phải cập nhật `types.ts` tương ứng cùng lúc — không để lệch ngầm.
- TypeScript strict mode; không dùng `any` trừ khi có comment giải thích lý do.
- Component chỉ xử lý trình bày (UI) và gọi composable/store; logic nghiệp vụ (tính giá, validate phức tạp) đặt trong composable hoặc store, không viết trong `<script setup>` của component trang.

---

## 6. Realtime / WebSocket Architecture 

Áp dụng cho Chat (SEL-16, CUS-20), thông báo realtime (BON-08), Flash Sale realtime (BON-14).

- **Consumer chỉ nhận và phát message — không chứa business logic.** Logic (lưu tin nhắn, tính unread count, validate quyền truy cập hội thoại...) nằm ở Service Layer, consumer chỉ gọi service.
- **Group naming theo quy ước cố định:**
  - Thông báo cá nhân: `user_{user_id}`
  - Thông báo theo shop: `shop_{shop_id}`
  - Hội thoại chat: `conversation_{conversation_id}`
- **Xác thực WebSocket bắt buộc** ở bước handshake (JWT qua query param hoặc subprotocol) — không cho phép kết nối ẩn danh vào các group riêng tư.
- Mọi message gửi qua WebSocket cũng phải được ghi vào DB (không dùng WebSocket làm nguồn dữ liệu duy nhất), để đảm bảo lấy lại lịch sử khi client reconnect.
- Có cơ chế fallback (polling) khi WebSocket không khả dụng, đặc biệt cho notification (đã nêu ở CUS-21).

---

## 7. AI Architecture 

Không gọi trực tiếp OpenAI/Claude/Gemini trong View:

```
AIService
   ↓
Provider (interface chung)
   ↓
OpenAIProvider / ClaudeProvider / GeminiProvider
```

Không phụ thuộc vào một nhà cung cấp AI (provider-agnostic), khớp với AI-15. `AIService` là tầng duy nhất được phép gọi ra provider bên ngoài.

**Yêu cầu bắt buộc đối với AIService** (không phải tùy chọn):
- **Retry & timeout:** mọi lời gọi provider phải có timeout và cơ chế retry có backoff.
- **Đếm token & chi phí:** ghi lại số token input/output và chi phí ước tính cho mỗi lần gọi.
- **Log prompt/response:** lưu vào bảng `AIRequestLog` (model, prompt, response, token, latency, lỗi nếu có) phục vụ debug và báo cáo đồ án.
- **Cache kết quả:** với các tác vụ không đổi theo thời gian thực (tóm tắt mô tả, tóm tắt review), cache theo key nội dung (hash) để tránh gọi lại thừa.
- **Fallback khi provider lỗi:** trả về kết quả suy giảm nhẹ (degrade gracefully) — ví dụ ẩn khối gợi ý AI, không để lỗi AI làm sập luồng nghiệp vụ chính (checkout, xem sản phẩm vẫn phải chạy được dù AI service down).
- **Tính toán số liệu bằng SQL trước, không để LLM tự tính toán số** (áp dụng cho AI-14 Sales Analytics) — chỉ đưa số liệu đã tính sẵn vào prompt để LLM diễn giải.
- Mọi nội dung do AI sinh ra hiển thị cho người dùng cuối phải có nhãn rõ ràng (ví dụ "Tạo bởi AI") như đã nêu ở AI-07.

---

## 8. Data Integrity & Concurrency 

Đây là nhóm rủi ro cao nhất của hệ thống (trừ tồn kho, Flash Sale, checkout nhiều shop cùng lúc, ví điện tử, điểm thưởng).

- **Mọi thao tác làm thay đổi số dư/tồn kho** (trừ tồn khi đặt hàng, hoàn tồn khi hủy, cộng/trừ ví, tích/tiêu điểm thưởng) **bắt buộc** nằm trong `transaction.atomic()` kết hợp khóa dòng (`select_for_update()`) hoặc dùng `F()` expression để tránh race condition.
- **Cấm read-modify-write không khóa** — không được đọc giá trị hiện tại ra Python, tính toán, rồi ghi đè lại (`obj.stock = obj.stock - qty; obj.save()`), vì đây là nguồn gốc phổ biến nhất của lỗi oversell.
- **Số dư không bao giờ được set trực tiếp.** Ví điện tử, điểm thưởng, tồn kho: mọi thay đổi phải đi qua một service duy nhất, ghi lại thành bản ghi giao dịch dạng append-only (`StockMovement`, `WalletTransaction`, `PointTransaction`) — không update trực tiếp cột `balance`/`stock`.
- **Ràng buộc ở tầng DB**, không chỉ ở tầng ứng dụng: `CheckConstraint` đảm bảo tồn kho/số dư không âm.
- Test bắt buộc phải có ít nhất 1 test case mô phỏng concurrent request để chống oversell (khớp NFR-14).

---

## 9. Database Principles 

Mọi bảng phải có:
- `created_at`
- `updated_at`

Nếu cần soft delete, dùng **đồng thời cả hai trường sau** (chuẩn hóa toàn dự án, không để mỗi module tự chọn một kiểu):
- `is_deleted` (boolean, dùng để filter nhanh, có index)
- `deleted_at` (datetime, ghi lại thời điểm xóa, dùng cho audit)

Ưu tiên Foreign Key thay vì lưu ID thủ công.

Đặt Index cho:
- email
- slug
- status
- created_at

**Kiểu dữ liệu tiền tệ:** luôn dùng `DecimalField`, không dùng `Float` cho bất kỳ giá trị tiền nào (giá sản phẩm, doanh thu, số dư ví, hoa hồng...). Quy ước làm tròn đơn vị VNĐ tới hàng đơn vị, không dùng phần thập phân trừ khi có yêu cầu khác.

**Thời gian:** lưu trữ theo UTC trong database (`USE_TZ = True`); chỉ convert sang giờ Việt Nam (UTC+7) ở tầng hiển thị (Serializer/Frontend).

---

## 10. API Design

RESTful API.

```
GET
POST
PUT
PATCH
DELETE
```

Không sử dụng:
```
/getProducts
/updateProduct
```

Mà sử dụng:
```
GET   /products
POST  /products
PATCH /products/{id}
```

---

## 11. Response Format 

Mọi API trả về cùng một cấu trúc.

Thành công:
```json
{
    "success": true,
    "message": "...",
    "data": {}
}
```

Lỗi:
```json
{
    "success": false,
    "message": "...",
    "errors": {}
}
```

**Danh sách phân trang** (áp dụng cho mọi API list — Admin, Seller, Customer) dùng thêm khối `meta` cố định:
```json
{
    "success": true,
    "message": "...",
    "data": [ ... ],
    "meta": {
        "page": 1,
        "page_size": 20,
        "total_items": 134,
        "total_pages": 7
    }
}
```

---

## 12. Error Handling

Không trả Exception trực tiếp. Luôn xử lý:
- Validation Error
- Permission Error
- Authentication Error
- Business Error
- System Error

---

## 13. Authentication

Sử dụng:
- JWT Authentication
- Role
- Permission

Không hard-code Role.

---

## 14. Multi-tenant Data Isolation 

Nguyên tắc riêng cho hệ thống marketplace đa gian hàng — đây là lỗ hổng bảo mật phổ biến nhất của loại hệ thống này nên tách thành mục riêng thay vì gộp chung Authorization.

- **Mọi query của Seller phải luôn được scope theo `shop_id` của chính seller đang đăng nhập, ở tầng Service/Repository — không bao giờ dựa vào tham số do FE gửi lên để lọc.**
- Không tin `shop_id`/`user_id` gửi từ client trong request body hay query param khi xác định quyền sở hữu dữ liệu; luôn lấy từ `request.user`.
- Object-level permission bắt buộc cho mọi endpoint chạm vào dữ liệu thuộc về một shop hoặc một khách hàng cụ thể (đơn hàng, sản phẩm, kho, voucher...).
- Viết test riêng đảm bảo Seller A không thể đọc/sửa dữ liệu của Seller B qua việc đổi ID trên URL (khớp NFR-02, NFR-14).

---

## 15. Payment & Webhook Idempotency 

Áp dụng cho CUS-15 (thanh toán) và mọi webhook/callback từ bên thứ ba.

- Mọi endpoint nhận callback/IPN từ cổng thanh toán **phải idempotent** — gọi lại nhiều lần với cùng dữ liệu không được tạo thêm giao dịch hay cộng/trừ tiền thêm lần nữa.
- Lưu lại **toàn bộ** payload callback vào bảng `PaymentTransaction`/log trước khi xử lý, dùng mã giao dịch (transaction reference) làm khóa duy nhất để chống xử lý trùng.
- Trạng thái đơn hàng chỉ được cập nhật qua một service duy nhất nhận callback, không cho phép nhiều luồng cùng cập nhật trạng thái thanh toán của một đơn.

---

## 16. Naming Convention

- Class: `ProductService`
- Model: `Product`
- Serializer: `ProductSerializer`
- Permission: `IsSeller`
- Task: `GenerateEmbeddingTask`

---

## 17. Docker & Deployment 

Toàn bộ hệ thống phải chạy được bằng `docker-compose` với một lệnh duy nhất (sản phẩm bàn giao bắt buộc theo đặc tả).

- Dockerfile cho Frontend và Backend đều dùng **multi-stage build** (build riêng, runtime riêng — không đóng gói công cụ build vào image chạy thật).
- Mỗi service (frontend, backend, celery worker, celery beat, redis) phải có **healthcheck** riêng trong `docker-compose.yml`.
- PostgreSQL chạy **bên ngoài** docker-compose, kết nối qua biến môi trường (theo đúng đặc tả).
- Không hardcode cấu hình (host, port, secret) trong Dockerfile hay image — toàn bộ qua biến môi trường/`.env`.
- Nginx làm reverse proxy: `/` → static FE, `/api` và `/ws` → backend.

---

## 18. CI/CD 

- Pipeline tối thiểu (GitHub Actions) chạy khi push/tạo PR:
  - **Backend job:** lint (`ruff`) + test (`pytest`)
  - **Frontend job:** lint (`eslint`) + test (`vitest`) + build (`vite build`)
- **Không merge vào `develop`/`main` khi pipeline thất bại.**
- Build Docker image tự động khi merge vào `main` (điểm cộng theo đặc tả, không bắt buộc).

---

## 19. Git Convention

Branch:
```
main
develop
feature/*
hotfix/*
```

Commit:
```
feat:
fix:
refactor:
docs:
test:
style:
chore:
```

---

## 20. Testing **[CẬP NHẬT — chốt số liệu cụ thể]**

Mỗi chức năng quan trọng nên có:
- Unit Test
- API Test
- Permission Test

**Không merge khi test thất bại.**

Chốt theo NFR-14, đưa thẳng vào ràng buộc bắt buộc (không chỉ là mục tiêu điểm số):
- **Độ phủ test tối thiểu 60%** cho các module core: giỏ hàng, checkout, voucher, tồn kho.
- **Bắt buộc có test case mô phỏng concurrent request** để chống oversell tồn kho (liên kết mục 8 — Data Integrity).
- Backend: `pytest` + `pytest-django` + `factory_boy`. Frontend: `vitest` + `@vue/test-utils` cho component/store quan trọng.

---

## 21. Logging

Không dùng `print()`.

Sử dụng `logging` hoặc `loguru`.

Log có cấu trúc (structured logging) gắn kèm `request_id`, `user_id`; log riêng cho lỗi thanh toán và lỗi gọi AI provider (khớp NFR-15).

---

## 22. Security

- Không commit `.env`.
- Không commit Secret Key, API Key, Database Password.
- Sử dụng biến môi trường.

---

## 23. Performance

Ưu tiên:
- `select_related()`
- `prefetch_related()`

Không để xảy ra N+1 Query.

---

## 24. Feature Flag & System Config 

Khớp với ADM-26.

- Các tính năng lớn, đặc biệt là tính năng AI, nên có khả năng bật/tắt qua bảng `SiteSetting` (key-value, có cache) mà **không cần deploy lại**.
- Dùng để giảm rủi ro: nếu một tính năng AI gây lỗi hoặc tốn chi phí bất thường, có thể tắt ngay mà không ảnh hưởng luồng nghiệp vụ chính.

---

## 25. Internationalization (i18n) 

Áp dụng khi triển khai AI-12 (dịch mô tả sản phẩm).

- Bản dịch lưu ở bảng riêng (`ProductTranslation`: `product`, `lang`, các trường đã dịch), **không ghi đè** lên bản gốc.
- Giữ nguyên format HTML/rich-text khi dịch.

---

## 26. Documentation

Mỗi module cần có:
- README
- API Document
- Database Design

Khi thêm tính năng mới cần cập nhật tài liệu.

---

## 27. AI Coding Rules

Khi AI sinh code phải:
- Giải thích trước khi viết.
- Giải thích sau khi viết.
- Không bỏ qua bước phân tích.
- Không viết toàn bộ logic trong View.
- Tuân thủ Clean Architecture.
- Ưu tiên khả năng mở rộng.
- Đề xuất cải tiến nếu phát hiện thiết kế chưa hợp lý.
- Nếu có nhiều phương án, phải so sánh ưu và nhược điểm trước khi lựa chọn.

---

## 28. Definition of Done

Một task chỉ được xem là hoàn thành khi đáp ứng đầy đủ:
- Đã phân tích yêu cầu.
- Đã thiết kế cơ sở dữ liệu (nếu có).
- Đã thiết kế API (nếu có).
- Đã triển khai mã nguồn.
- Đã giải thích mã nguồn.
- Đã kiểm thử.
- Đã xử lý các trường hợp lỗi.
- Đã cập nhật tài liệu liên quan.

---

## 29. Project Goal

Mục tiêu cuối cùng của dự án không chỉ là xây dựng một website thương mại điện tử hoạt động được, mà còn tạo ra một hệ thống có kiến trúc rõ ràng, mã nguồn dễ bảo trì, dễ mở rộng và tuân thủ các thực tiễn tốt trong phát triển phần mềm. Toàn bộ quá trình phát triển cần hướng đến chất lượng của một sản phẩm thực tế, đồng thời giúp người thực hiện hiểu được lý do đằng sau mỗi quyết định thiết kế và triển khai.
