# Tech Stack

Nguồn: sheet "Công nghệ" trong `Dac-ta-yeu-cau-He-thong-ban-hang-AI.xlsx`. Đây là danh sách công nghệ **bắt buộc/khuyến nghị** cho dự án; các lựa chọn có ghi "chọn 1" thì cần chốt và dùng nhất quán toàn dự án ngay từ đầu.

## 1. Frontend

| Công nghệ | Phiên bản / Yêu cầu | Ghi chú |
|---|---|---|
| Node.js | 22 LTS (>=22.12) | Môi trường build & dev server; nâng từ Node 20 đã EOL, xem Decision C1. |
| Vue.js | 3.x — Composition API + `<script setup>` | Framework SPA chính. |
| TypeScript | 5.x, strict mode | Bắt buộc toàn bộ code FE có type. |
| Vite | 8.x | Build tool & dev server; nâng khỏi dải phiên bản có security advisory, xem Decision C1. |
| Pinia | 2.x | State management (auth, cart, notification...). |
| Vue Router | 4.x | Routing + route guard theo vai trò. |
| CSS Framework | Tailwind CSS (khuyến nghị) hoặc Bootstrap 5 | Chọn 1, dùng nhất quán toàn dự án. |
| Icon | Heroicons hoặc FontAwesome | Chọn 1 bộ icon thống nhất. |
| HTTP Client | Axios | Instance chung + interceptor refresh token. |
| Biểu đồ | Chart.js / ApexCharts | Dùng cho Dashboard Admin & Seller. |

## 2. Backend

| Công nghệ | Phiên bản / Yêu cầu | Ghi chú |
|---|---|---|
| Python | 3.12 | Phiên bản cố định trong Dockerfile. |
| Django | 5.x | Framework chính. |
| Django REST Framework | 3.15+ | Xây dựng REST API. |
| Xác thực | `djangorestframework-simplejwt` | JWT access + refresh, blacklist. |
| Django Channels | 4.x | WebSocket: chat, thông báo realtime. |
| Celery + Celery Beat | 5.x | Background job & job định kỳ. |
| API Docs | `drf-spectacular` | Swagger / OpenAPI tự sinh. |

## 3. Database

| Công nghệ | Phiên bản / Yêu cầu | Ghi chú |
|---|---|---|
| PostgreSQL | External (ngoài docker-compose), cấu hình qua env | DB chính; bật extension `pg_trgm`. |
| pgvector | Extension trên PostgreSQL | Lưu embeddings cho semantic search / recommendation. |
| Redis | 7.x (trong docker-compose) | Cache, Celery broker, Channels layer. |

## 4. AI

| Công nghệ | Phiên bản / Yêu cầu | Ghi chú |
|---|---|---|
| LLM Provider | OpenAI / Anthropic Claude / Google Gemini (chọn 1+) | Key qua biến môi trường; luôn qua AI Service Layer chung (xem `ARCHITECTURE.md` mục AI Architecture). |
| Embedding model | Model đa ngôn ngữ hỗ trợ tiếng Việt | Dùng cho smart search & recommendation. |

## 5. DevOps

| Công nghệ | Phiên bản / Yêu cầu | Ghi chú |
|---|---|---|
| Docker + docker-compose | Compose chạy toàn bộ stack 1 lệnh | Dockerfile cho FE và BE (multi-stage). |
| Nginx | Reverse proxy + serve static FE | Proxy `/api`, `/ws`; gzip; cache asset. |
| CI/CD | GitHub Actions (khuyến nghị) | Lint + test + build image. |

## 6. Khác

| Công nghệ | Phiên bản / Yêu cầu | Ghi chú |
|---|---|---|
| Git | Git flow đơn giản (`main` / `develop` / `feature/*`) | Commit message rõ ràng; PR tự review. |

## 7. Các quyết định cần chốt trước khi code

Trước khi bắt đầu triển khai, nhóm cần chốt các lựa chọn "chọn 1" sau đây và ghi lại lý do (đúng nguyên tắc AI Coding Rules trong `PROJECT_CONSTITUTION.md` — nếu có nhiều phương án phải so sánh ưu/nhược trước khi chọn):

- [ ] CSS framework: Tailwind CSS hay Bootstrap 5?
- [ ] Bộ icon: Heroicons hay FontAwesome?
- [ ] Thư viện biểu đồ: Chart.js hay ApexCharts?
- [ ] LLM Provider chính: OpenAI, Claude, hay Gemini? (Kiến trúc AI Service Layer vẫn phải provider-agnostic dù chọn provider nào làm mặc định.)
- [ ] Embedding model cụ thể (ví dụ `text-embedding-3-small` hay model tiếng Việt riêng).
- [ ] Cổng thanh toán sandbox tích hợp thêm ngoài COD: VNPay / MoMo / Stripe test.

## 8. Tài liệu liên quan

- `PROJECT_OVERVIEW.md` — mục tiêu & phạm vi dự án.
- `ARCHITECTURE.md` — cách các công nghệ trên được ghép lại thành kiến trúc hệ thống.
- `CODING_STANDARDS.md` — quy chuẩn sử dụng các công nghệ trên trong code.
