# Project Context

Nguồn: `PROJECT_OVERVIEW.md`, `TECH_STACK.md`, `ARCHITECTURE.md`, `PROJECT_CONSTITUTION.md` mục 1.

## 1. Giới thiệu
| | |
|---|---|
| **Tên dự án** | Multi-Vendor AI E-commerce Platform |
| **Loại** | Đồ án thực tập/tốt nghiệp Fullstack |
| **Frontend** | Vue.js 3 (Composition API + `<script setup>`) + TypeScript |
| **Backend** | Django 5.x + Django REST Framework |
| **Database** | PostgreSQL (external) + pgvector + Redis |
| **Triển khai** | Docker / docker-compose + Nginx |
| **Đặc thù** | Tích hợp AI xuyên suốt (search, gợi ý, chatbot, hỗ trợ seller, phân tích) |

**Mục tiêu:** không chỉ chạy được, mà phải đạt chất lượng sản phẩm thực tế — kiến trúc rõ ràng, dễ bảo trì, dễ mở rộng, và người thực hiện hiểu rõ lý do đằng sau từng quyết định thiết kế.

## 2. Vai trò người dùng (3 role)

| Vai trò | Mô tả | Sheet đặc tả |
|---|---|---|
| **Admin hệ thống** | Quản trị toàn sàn: người dùng, seller, sản phẩm, đơn hàng, khuyến mãi, báo cáo. | Admin |
| **Nhà bán hàng (Seller)** | Quản lý gian hàng: sản phẩm, kho, đơn hàng, voucher shop, chat với khách. | Seller |
| **Khách hàng (Customer)** | Mua sắm: tìm kiếm, giỏ hàng, đặt hàng, thanh toán, đánh giá, chat. | Customer |

Phân quyền dựa trên JWT claim + DRF Permission (BE) và Vue Router guard (FE, chỉ là UX — không thay thế permission check BE). Xem `ARCHITECTURE.md` mục 4.

## 3. Phạm vi yêu cầu (111 yêu cầu)

| Nhóm | Tổng | Bắt buộc | Nên có | Tùy chọn |
|---|---|---|---|---|
| Admin | 26 | 16 | 8 | 2 |
| Seller | 18 | 14 | 4 | 0 |
| Customer | 22 | 19 | 2 | 1 |
| Tính năng AI | 15 | 5 | 3 | 7 |
| Bonus | 14 | 0 | 2 | 12 |
| Phi chức năng | 16 | 11 | 4 | 1 |
| **TỔNG** | **111** | **65** | **23** | **23** |

Thứ tự làm: **Bắt buộc → Nên có → Tùy chọn**. Danh sách đầy đủ từng mã YC ở `feature_checklist.md`.

## 4. Nhóm chức năng chính

- **Admin:** dashboard thống kê, quản lý người dùng/seller/sản phẩm/đơn hàng, khuyến mãi cấp sàn, báo cáo, audit log, cấu hình hệ thống.
- **Seller:** dashboard gian hàng, CRUD sản phẩm + biến thể, quản lý kho, xử lý đơn hàng, voucher shop, chat với khách, trang gian hàng công khai.
- **Customer:** tài khoản & xác thực, tìm kiếm & lọc, chi tiết sản phẩm, wishlist, giỏ hàng, checkout & thanh toán, theo dõi đơn hàng, đánh giá, chat, thông báo.
- **AI:** smart search, semantic search (embeddings), gợi ý cá nhân hóa, chatbot tư vấn, tóm tắt review/mô tả, so sánh sản phẩm, hỗ trợ seller (sinh mô tả, auto-tag, dịch, gợi ý giá), phân tích doanh số AI, AI Service Layer dùng chung.
- **Bonus:** theo dõi vận chuyển, follow shop, combo sản phẩm, affiliate, loyalty (điểm thưởng, ví điện tử), realtime nâng cao, waitlist, báo cáo vi phạm, import/export Excel, QR code, xu hướng sản phẩm.
- **Phi chức năng:** bảo mật, hiệu năng, kiến trúc, triển khai, chất lượng (testing), vận hành (logging, backup).

## 5. Kiến trúc tổng thể (tóm tắt)

```
Presentation Layer      ← Vue 3 components, Django Views/Serializers
      ↓
Application Layer       ← Service Layer (business logic)
      ↓
Domain Layer             ← Models, business rules
      ↓
Infrastructure Layer     ← Database, Redis, Celery, AI Providers, Payment Gateway
```

Backend: mỗi module nghiệp vụ = 1 Django app độc lập (`apps/<module>/`), cấu trúc thống nhất `models / serializers / views / services / repositories / permissions / validators / selectors / tasks / signals / tests`. Không bắt buộc dùng hết — chỉ tạo file khi thật sự cần.

Frontend: tổ chức theo domain (`features/<domain>/`), không theo loại file. Component không gọi axios trực tiếp — luôn qua `api.ts` của feature.

Chi tiết đầy đủ (Realtime/WebSocket, AI, Data Integrity, Multi-tenant, Deployment) ở `ARCHITECTURE.md`.

## 6. Rủi ro kỹ thuật lớn nhất của hệ thống

1. **Race condition** trên tồn kho / Flash Sale / checkout nhiều shop / ví điện tử / điểm thưởng.
2. **Rò rỉ dữ liệu chéo shop** (Seller A đọc được dữ liệu Seller B) — lỗ hổng phổ biến nhất của marketplace.
3. **Lỗi AI provider làm sập luồng nghiệp vụ chính** nếu không có fallback đúng chuẩn.
4. **Webhook thanh toán không idempotent** gây cộng/trừ tiền sai khi cổng thanh toán gọi lại.

Quy tắc xử lý các rủi ro này là **bắt buộc**, không phải khuyến nghị — xem `PROJECT_CONSTITUTION.md` mục 8, 14, 15 và `ai_rules.md` Phần B.

## 7. Sản phẩm bàn giao

1. Source code FE (Vue 3 + TS) và BE (Django) trên Git, có README hướng dẫn chạy.
2. `docker-compose.yml` chạy toàn bộ hệ thống bằng 1 lệnh (FE, BE, Celery, Redis, Nginx; PostgreSQL external qua env).
3. Tài liệu API (Swagger/OpenAPI) và sơ đồ ERD.
4. `.env.example` liệt kê đầy đủ biến môi trường.
5. Seed data mẫu (danh mục, sản phẩm, tài khoản 3 vai trò) để demo ngay.
6. Bản demo + slide trình bày kiến trúc, luồng nghiệp vụ chính, tính năng AI đã làm.

## 8. Tiêu chí đánh giá (trọng số)

| Nhóm tiêu chí | Trọng số | Nội dung |
|---|---|---|
| Bắt buộc | 40% | Authentication, Authorization, CRUD, Kho, Giỏ hàng/Đặt hàng, Dashboard |
| Nâng cao | 20% | Upload, phân trang/lọc, Voucher/Wishlist, Review, Chat/Thông báo |
| AI | 25% | Smart search, Chatbot, Sinh mô tả/tóm tắt, Gợi ý sản phẩm |
| Bonus | 15% | WebSocket/Background job/Cache, Vector search, Docker/CI-CD, Testing/Logging |

## 9. Công nghệ (tóm tắt — chi tiết ở `TECH_STACK.md`)

| Lớp | Công nghệ |
|---|---|
| Frontend | Node 22 LTS (>=22.12), Vue 3, TypeScript 5 strict, Vite 8, Pinia 2, Vue Router 4, Axios |
| Backend | Python 3.12, Django 5.x, DRF 3.15+, `djangorestframework-simplejwt`, Django Channels 4.x, Celery + Beat 5.x, `drf-spectacular` |
| Database | PostgreSQL (external) + pgvector, Redis 7.x |
| AI | OpenAI / Anthropic Claude / Google Gemini (chọn ≥1, provider-agnostic qua `AIService`) |
| DevOps | Docker + docker-compose (multi-stage), Nginx reverse proxy, GitHub Actions |

Một số lựa chọn "chọn 1" (CSS framework, icon set, chart lib, LLM provider mặc định, embedding model, cổng thanh toán sandbox) **chưa được chốt** — xem `decision_log.md`.

## 10. Tài liệu liên quan

- `system_prompt.md` — cách AI nên vận hành trong dự án này.
- `ai_rules.md` — quy tắc AI (coding assistant + AIService trong sản phẩm).
- `feature_checklist.md` — danh sách đầy đủ 111 yêu cầu.
- `decision_log.md` — quyết định đã chốt & còn tồn đọng.
- Tài liệu gốc: `PROJECT_OVERVIEW.md`, `TECH_STACK.md`, `ARCHITECTURE.md`, `PROJECT_CONSTITUTION.md`, `CODING_STANDARDS.md`, `api_design.md`, `database_design.md`, `coding_patterns.md`, `folder_structure.md`, `Dac-ta-yeu-cau-He-thong-ban-hang-AI.xlsx`.
