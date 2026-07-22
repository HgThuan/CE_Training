# Project Overview

## 1. Giới thiệu

**Tên dự án:** Multi-Vendor AI E-commerce Platform
**Loại:** Đồ án thực tập Fullstack
**Stack:** Vue.js 3 + TypeScript (Frontend) / Django + Python 3.12 (Backend) / PostgreSQL (Database) / Docker (Triển khai) — tích hợp AI

## 2. Mục tiêu

Xây dựng một sàn thương mại điện tử đa gian hàng (multi-vendor) gồm 3 vai trò: Admin hệ thống, Nhà bán hàng (Seller) và Khách hàng (Customer). Hệ thống hỗ trợ đầy đủ nghiệp vụ bán hàng (sản phẩm, kho, giỏ hàng, đặt hàng, khuyến mãi, đánh giá, chat) và tích hợp AI để nâng cao trải nghiệm tìm kiếm, mua sắm và quản trị.

Mục tiêu không chỉ dừng ở việc chạy được, mà hướng tới chất lượng của một sản phẩm thực tế: kiến trúc rõ ràng, dễ bảo trì, dễ mở rộng (xem thêm `PROJECT_CONSTITUTION.md` và `ARCHITECTURE.md`).

## 3. Vai trò người dùng

| Vai trò | Mô tả | Sheet chi tiết trong Đặc tả |
|---|---|---|
| **Admin hệ thống** | Quản trị toàn sàn: người dùng, seller, sản phẩm, đơn hàng, khuyến mãi, báo cáo. | Admin |
| **Nhà bán hàng (Seller)** | Quản lý gian hàng: sản phẩm, kho, đơn hàng, voucher shop, chat với khách. | Seller |
| **Khách hàng (Customer)** | Mua sắm: tìm kiếm, giỏ hàng, đặt hàng, thanh toán, đánh giá, chat với shop. | Customer |

## 4. Phạm vi & thống kê yêu cầu

Tổng cộng **111 yêu cầu**, chia theo nhóm và độ ưu tiên:

| Nhóm yêu cầu | Tổng số | Bắt buộc | Nên có | Tùy chọn |
|---|---|---|---|---|
| Admin | 26 | 16 | 8 | 2 |
| Seller | 18 | 14 | 4 | 0 |
| Customer | 22 | 19 | 2 | 1 |
| Tính năng AI | 15 | 5 | 3 | 7 |
| Bonus | 14 | 0 | 2 | 12 |
| Phi chức năng | 16 | 11 | 4 | 1 |
| **TỔNG** | **111** | **65** | **23** | **23** |

Quy ước độ ưu tiên:
- **Bắt buộc** — phải hoàn thành để dự án được xem là đạt.
- **Nên có** — làm sau khi đã xong toàn bộ phần Bắt buộc.
- **Tùy chọn** — điểm cộng, làm nếu còn thời gian.

Chi tiết từng yêu cầu (mã YC, mô tả, gợi ý kỹ thuật, trạng thái) nằm trong file đặc tả gốc `Dac-ta-yeu-cau-He-thong-ban-hang-AI.xlsx`, mỗi sheet tương ứng một nhóm ở trên.

## 5. Nhóm chức năng chính

- **Quản trị (Admin):** dashboard thống kê, quản lý người dùng/seller/sản phẩm/đơn hàng, khuyến mãi cấp sàn, báo cáo, audit log, cấu hình hệ thống.
- **Bán hàng (Seller):** dashboard gian hàng, CRUD sản phẩm + biến thể, quản lý kho (nhập/xuất/tồn), xử lý đơn hàng, voucher shop, chat với khách, trang gian hàng công khai.
- **Mua sắm (Customer):** tài khoản & xác thực, tìm kiếm & lọc, chi tiết sản phẩm, wishlist, giỏ hàng, checkout & thanh toán, theo dõi đơn hàng, đánh giá, chat, thông báo.
- **Tính năng AI:** smart search theo nhu cầu, semantic search (embeddings), gợi ý cá nhân hóa, chatbot tư vấn, tóm tắt review/mô tả sản phẩm, so sánh sản phẩm, hỗ trợ seller (sinh mô tả, auto-tag, dịch, gợi ý giá), phân tích doanh số bằng AI, AI Service Layer dùng chung.
- **Bonus (điểm cộng):** theo dõi vận chuyển, follow shop, combo sản phẩm, affiliate, loyalty (điểm thưởng, ví điện tử), realtime nâng cao, waitlist, báo cáo vi phạm, import/export Excel, QR code, xu hướng sản phẩm.
- **Phi chức năng:** bảo mật (xác thực, phân quyền, chống tấn công, quản lý secrets), hiệu năng (phân trang, cache, background job), kiến trúc (API design, cấu trúc code FE, database design), triển khai (Docker, Nginx, CI/CD), chất lượng (testing), vận hành (logging, backup).

## 6. Sản phẩm bàn giao

1. Source code Frontend (Vue 3 + TypeScript) và Backend (Django) trên Git repository, có README hướng dẫn chạy.
2. `docker-compose.yml` chạy được toàn bộ hệ thống bằng 1 lệnh (FE, BE, Celery, Redis, Nginx; PostgreSQL external qua env).
3. Tài liệu API (Swagger/OpenAPI) và sơ đồ ERD cơ sở dữ liệu.
4. File `.env.example` liệt kê đầy đủ biến môi trường (DB, JWT secret, AI API key, payment sandbox...).
5. Seed data mẫu (danh mục, sản phẩm, tài khoản 3 vai trò) để demo được ngay.
6. Bản demo + slide trình bày: kiến trúc hệ thống, luồng nghiệp vụ chính, các tính năng AI đã làm.

## 7. Tiêu chí đánh giá (tóm tắt trọng số)

| Nhóm tiêu chí | Trọng số |
|---|---|
| Bắt buộc (Authentication, Authorization, CRUD, Kho, Giỏ hàng/Đặt hàng, Dashboard) | 40% |
| Nâng cao (Upload, phân trang/lọc, Voucher/Wishlist, Review, Chat/Thông báo) | 20% |
| AI (Smart search, Chatbot, Sinh mô tả/tóm tắt, Gợi ý sản phẩm) | 25% |
| Bonus (WebSocket/Background job/Cache, Vector search, Docker/CI-CD, Testing/Logging) | 15% |

Chi tiết từng tiêu chí và mã yêu cầu liên quan nằm ở sheet "Đánh giá" trong file đặc tả gốc.

## 8. Tài liệu liên quan

- `Dac-ta-yeu-cau-He-thong-ban-hang-AI.xlsx` — đặc tả yêu cầu chi tiết (nguồn gốc của tài liệu này).
- `PROJECT_CONSTITUTION.md` — nguyên tắc thiết kế & quy ước bắt buộc trong suốt dự án.
- `TECH_STACK.md` — công nghệ & phiên bản sử dụng.
- `ARCHITECTURE.md` — kiến trúc hệ thống chi tiết.
- `CODING_STANDARDS.md` — quy chuẩn viết code, API, testing, git.
