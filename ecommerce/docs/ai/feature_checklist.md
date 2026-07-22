# Feature Checklist

Nguồn: `Dac-ta-yeu-cau-He-thong-ban-hang-AI.xlsx` (9 sheet), đối chiếu `PROJECT_OVERVIEW.md` mục 4. Trạng thái gốc trong file đặc tả: toàn bộ **111/111 mục đang "Chưa làm"** tại thời điểm tổng hợp tài liệu này — checklist dưới dùng để theo dõi tiến độ từ đây.

Ký hiệu độ ưu tiên: 🔴 Bắt buộc · 🟡 Nên có · ⚪ Tùy chọn. Thứ tự triển khai luôn là **🔴 → 🟡 → ⚪**.

Cập nhật trạng thái bằng cách tick `[x]` khi mã YC hoàn thành đủ Definition of Done (`system_prompt.md` mục 5).

---

## A. Admin (26 yêu cầu — 16 🔴 / 8 🟡 / 2 ⚪)

### Dashboard
- [ ] 🔴 **ADM-01** — Thẻ thống kê tổng quan
- [ ] 🔴 **ADM-02** — Biểu đồ doanh thu
- [ ] 🔴 **ADM-03** — Top sản phẩm bán chạy

### Quản lý người dùng
- [x] 🔴 **ADM-04** — CRUD khách hàng
- [ ] 🔴 **ADM-05** — CRUD nhà bán hàng
- [x] 🔴 **ADM-06** — Khóa / mở khóa tài khoản
- [x] 🔴 **ADM-07** — Reset mật khẩu người dùng
- [x] 🔴 **ADM-08** — Phân quyền (RBAC)

### Quản lý seller
- [ ] 🔴 **ADM-09** — Duyệt đăng ký seller
- [ ] 🟡 **ADM-10** — Xác minh thông tin gian hàng
- [ ] 🔴 **ADM-11** — Khóa gian hàng
- [ ] 🟡 **ADM-12** — Theo dõi doanh thu seller

### Quản lý sản phẩm
- [ ] 🟡 **ADM-13** — Duyệt sản phẩm
- [ ] 🔴 **ADM-14** — Ẩn / xóa sản phẩm vi phạm
- [ ] 🔴 **ADM-15** — Quản lý danh mục (đa cấp)
- [ ] 🔴 **ADM-16** — Quản lý thương hiệu

### Quản lý đơn hàng
- [ ] 🔴 **ADM-17** — Theo dõi đơn toàn hệ thống
- [ ] 🟡 **ADM-18** — Xử lý tranh chấp / khiếu nại

### Khuyến mãi
- [ ] 🟡 **ADM-19** — Quản lý Flash Sale
- [ ] 🔴 **ADM-20** — Quản lý Coupon toàn sàn
- [ ] 🔴 **ADM-21** — Quản lý Banner trang chủ

### Báo cáo
- [ ] 🟡 **ADM-22** — Top seller / khách hàng / danh mục
- [ ] 🟡 **ADM-23** — Tỷ lệ hoàn / hủy đơn
- [ ] ⚪ **ADM-24** — Xuất báo cáo Excel / PDF

### Hệ thống
- [ ] 🟡 **ADM-25** — Audit Log
- [ ] ⚪ **ADM-26** — Cấu hình hệ thống (Feature Flag / `SiteSetting`)

---

## B. Seller (18 yêu cầu — 14 🔴 / 4 🟡 / 0 ⚪)

### Dashboard
- [ ] 🔴 **SEL-01** — Thống kê gian hàng

### Quản lý sản phẩm
- [ ] 🔴 **SEL-02** — CRUD sản phẩm
- [ ] 🔴 **SEL-03** — Upload nhiều ảnh & video
- [ ] 🔴 **SEL-04** — Biến thể sản phẩm (size, màu...)
- [ ] 🟡 **SEL-05** — SKU & Barcode

### Quản lý kho
- [ ] 🔴 **SEL-06** — Nhập kho
- [ ] 🔴 **SEL-07** — Xuất kho & điều chỉnh tồn
- [ ] 🔴 **SEL-08** — Lịch sử nhập / xuất
- [ ] 🔴 **SEL-09** — Cảnh báo sắp hết hàng

### Quản lý đơn hàng
- [ ] 🔴 **SEL-10** — Luồng xử lý đơn
- [ ] 🟡 **SEL-11** — In phiếu giao / đóng gói

### Voucher
- [ ] 🔴 **SEL-12** — Voucher riêng của shop

### Khách hàng
- [ ] 🟡 **SEL-13** — Danh sách khách của shop

### Đánh giá
- [ ] 🔴 **SEL-14** — Trả lời review
- [ ] 🟡 **SEL-15** — Báo cáo review vi phạm

### Chat
- [ ] 🔴 **SEL-16** — Chat với khách hàng

### Hồ sơ shop
- [ ] 🔴 **SEL-17** — Trang gian hàng
- [ ] 🔴 **SEL-18** — Đăng ký bán hàng

---

## C. Customer (22 yêu cầu — 19 🔴 / 2 🟡 / 1 ⚪)

### Tài khoản
- [x] 🔴 **CUS-01** — Đăng ký
- [x] 🔴 **CUS-02** — Đăng nhập / đăng xuất
- [ ] ⚪ **CUS-03** — Google Login
- [x] 🔴 **CUS-04** — Quên mật khẩu
- [x] 🔴 **CUS-05** — Hồ sơ cá nhân
- [x] 🔴 **CUS-06** — Sổ địa chỉ

### Trang chủ
- [ ] 🔴 **CUS-07** — Banner & khối nội dung

### Tìm kiếm & Lọc
- [ ] 🔴 **CUS-08** — Tìm kiếm theo từ khóa
- [ ] 🔴 **CUS-09** — Bộ lọc & sắp xếp đa tiêu chí

### Chi tiết sản phẩm
- [ ] 🔴 **CUS-10** — Trang chi tiết
- [ ] 🔴 **CUS-11** — Review & hỏi đáp (Q&A)

### Wishlist
- [ ] 🔴 **CUS-12** — Sản phẩm yêu thích

### Giỏ hàng
- [ ] 🔴 **CUS-13** — Quản lý giỏ hàng

### Thanh toán
- [ ] 🔴 **CUS-14** — Checkout (tách đơn theo shop)
- [ ] 🔴 **CUS-15** — Phương thức thanh toán

### Đơn hàng
- [ ] 🔴 **CUS-16** — Theo dõi đơn hàng
- [ ] 🔴 **CUS-17** — Hủy đơn & mua lại
- [ ] 🟡 **CUS-18** — Yêu cầu trả hàng / hoàn tiền

### Đánh giá
- [ ] 🔴 **CUS-19** — Viết đánh giá

### Chat
- [ ] 🔴 **CUS-20** — Chat với shop

### Thông báo
- [ ] 🟡 **CUS-21** — Trung tâm thông báo

### Giao diện
- [ ] 🔴 **CUS-22** — Responsive & UX cơ bản

---

## D. Tính năng AI (15 yêu cầu — 5 🔴 / 3 🟡 / 7 ⚪)

### Tìm kiếm
- [ ] ⚪ **AI-01** — AI Smart Search (tìm theo nhu cầu)
- [ ] ⚪ **AI-02** — Semantic search bằng embeddings

### Gợi ý
- [ ] ⚪ **AI-03** — AI Recommendation cá nhân hóa
- [ ] ⚪ **AI-04** — AI Similar Products

### Trợ lý
- [ ] ⚪ **AI-05** — AI Shopping Assistant (chatbot)
- [ ] 🟡 **AI-06** — AI Customer Support tự động

### Nội dung
- [ ] 🔴 **AI-07** — AI Review Summary (nhãn "Tạo bởi AI" bắt buộc)
- [ ] 🔴 **AI-08** — AI Product Summary
- [ ] 🔴 **AI-09** — AI Compare (so sánh sản phẩm)

### Hỗ trợ seller
- [ ] 🔴 **AI-10** — AI Generate Description
- [ ] 🟡 **AI-11** — AI Auto Tag & phân loại
- [ ] ⚪ **AI-12** — AI Translate mô tả
- [ ] ⚪ **AI-13** — AI Price Suggestion

### Phân tích
- [ ] 🟡 **AI-14** — AI Sales Analytics (tính số bằng SQL trước, LLM chỉ diễn giải)

### Hạ tầng AI
- [ ] 🔴 **AI-15** — AI Service Layer chung (provider-agnostic, xem `ai_rules.md` Phần B)

---

## E. Bonus (14 yêu cầu — 0 🔴 / 2 🟡 / 12 ⚪)

- [ ] ⚪ **BON-01** — Theo dõi vận chuyển
- [ ] ⚪ **BON-02** — Follow shop
- [ ] ⚪ **BON-03** — Combo sản phẩm
- [ ] ⚪ **BON-04** — Mua kèm giảm giá
- [ ] ⚪ **BON-05** — Affiliate
- [ ] ⚪ **BON-06** — Điểm thưởng (loyalty)
- [ ] ⚪ **BON-07** — Ví điện tử nội bộ
- [ ] 🟡 **BON-08** — Thông báo realtime
- [ ] ⚪ **BON-09** — Waitlist khi hết hàng
- [ ] ⚪ **BON-10** — Báo cáo vi phạm
- [ ] 🟡 **BON-11** — Import / Export Excel
- [ ] ⚪ **BON-12** — QR đơn hàng & QR sản phẩm
- [ ] ⚪ **BON-13** — Gợi ý sản phẩm theo xu hướng
- [ ] ⚪ **BON-14** — Flash Sale realtime

---

## F. Phi chức năng (16 yêu cầu — 11 🔴 / 4 🟡 / 1 ⚪)

### Bảo mật
- [x] 🔴 **NFR-01** — Xác thực & phiên đăng nhập
- [x] 🔴 **NFR-02** — Phân quyền chặt ở API
- [ ] 🔴 **NFR-03** — Chống tấn công phổ biến
- [ ] 🔴 **NFR-04** — Quản lý secrets

### Hiệu năng
- [ ] 🔴 **NFR-05** — Phân trang & tối ưu truy vấn
- [ ] 🟡 **NFR-06** — Redis Cache
- [ ] 🔴 **NFR-07** — Background jobs

### Kiến trúc
- [ ] 🔴 **NFR-08** — Thiết kế API & tài liệu
- [ ] 🔴 **NFR-09** — Cấu trúc code FE
- [ ] 🔴 **NFR-10** — Database design

### Triển khai
- [ ] 🔴 **NFR-11** — Docker hóa toàn bộ
- [ ] 🔴 **NFR-12** — Nginx
- [ ] 🟡 **NFR-13** — CI/CD

### Chất lượng
- [ ] 🟡 **NFR-14** — Unit test & Integration test (≥60% module core + test concurrent chống oversell)

### Vận hành
- [ ] 🟡 **NFR-15** — Logging & giám sát
- [ ] ⚪ **NFR-16** — Sao lưu & khôi phục dữ liệu

---

## Tổng hợp

| Nhóm | Tổng | 🔴 Bắt buộc | 🟡 Nên có | ⚪ Tùy chọn |
|---|---|---|---|---|
| Admin | 26 | 16 | 8 | 2 |
| Seller | 18 | 14 | 4 | 0 |
| Customer | 22 | 19 | 2 | 1 |
| Tính năng AI | 15 | 5 | 3 | 7 |
| Bonus | 14 | 0 | 2 | 12 |
| Phi chức năng | 16 | 11 | 4 | 1 |
| **TỔNG** | **111** | **65** | **23** | **23** |

## Xác minh Sprint 1 — Authentication & User Foundation

Đối chiếu ngày 22/07/2026 với phạm vi Sprint 1 trong `AGILE_PROJECT_PLAN.md`:

| Hạng mục | Trạng thái | Bằng chứng chính |
|---|---|---|
| CUS-01 | Done | Đăng ký Customer, kiểm tra mật khẩu, email xác thực có hạn, Celery task và API test |
| CUS-02 | Done | JWT access/refresh, rotation + blacklist, cookie HttpOnly, axios interceptor và auth store |
| CUS-04 | Done | Luồng quên/đặt lại mật khẩu có token hết hạn và thu hồi toàn bộ phiên cũ |
| CUS-05 | Done | API `/me`, đổi mật khẩu, upload ảnh có giới hạn/kiểm tra nội dung, cắt vuông phía Frontend |
| CUS-06 | Done | CRUD địa chỉ theo owner, dropdown 3 cấp, duy nhất một mặc định, test chống truy cập chéo |
| NFR-01 | Done | Access ngắn hạn, refresh rotation/blacklist, hash mật khẩu, token không lưu URL/localStorage |
| Phần NFR-03 của Sprint 1 | Done một phần theo kế hoạch | Rate limit auth, ORM, lỗi production được ẩn, avatar validate và re-encode; NFR-03 tổng thể vẫn để `[ ]` vì upload/rich-text của các Sprint sau chưa triển khai |
| Phần NFR-04 của Sprint 1 | Done một phần theo kế hoạch | Secrets đọc từ môi trường, `.env` bị ignore, `.env.example` không chứa secret thật; NFR-04 tổng thể tiếp tục được rà soát khi thêm provider |
| Phần NFR-08 của Sprint 1 | Done một phần theo kế hoạch | API version `/api/v1`, response chuẩn hóa, schema OpenAPI của account validate thành công |
| Phần NFR-09 của Sprint 1 | Done một phần theo kế hoạch | Vue Composition API, Pinia, feature API layer, interceptor, ESLint/Prettier/type-check pass |

Lệnh xác minh: `TEST_USE_SQLITE=true pytest`, `ruff check .`, `python manage.py check`,
`python manage.py spectacular --validate`, `npm run lint`, `npm run format:check`,
`npm run test`, `npm run build`.

## Tài liệu liên quan

- File đặc tả gốc `Dac-ta-yeu-cau-He-thong-ban-hang-AI.xlsx` — mô tả chi tiết, độ khó, gợi ý kỹ thuật cho từng mã YC.
- `api_design.md` — endpoint cụ thể cho từng mã YC.
- `database_design.md` — bảng dữ liệu tương ứng.
- `project_context.md` — bối cảnh & tiêu chí đánh giá gắn với các nhóm trên.
