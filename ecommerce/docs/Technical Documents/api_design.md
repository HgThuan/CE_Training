# API Design

Tài liệu thiết kế API RESTful cho toàn bộ hệ thống, dựa trên `Dac-ta-yeu-cau-He-thong-ban-hang-AI.xlsx` và khớp với `database_design.md`. Quy chuẩn chung (naming, response format, error handling) đã định nghĩa ở `CODING_STANDARDS.md` mục 3–5 — tài liệu này liệt kê **endpoint cụ thể**.

## 0. Quy ước chung

- **Base path:** `/api/v1/`
- **Auth:** JWT Bearer token (`Authorization: Bearer <access_token>`), trừ endpoint đánh dấu **Public**.
- **JWT transport:** access token trả trong response và FE chỉ giữ trong memory; refresh token
  rotation được đặt trong cookie `HttpOnly` (mặc định path `/api/v1/auth/`). API client không dùng
  browser cookie có thể truyền `refresh` trong body của endpoint refresh/logout.
- **Phân trang:** query param `page`, `page_size`; response kèm khối `meta` (xem `CODING_STANDARDS.md` mục 4).
- **Lọc & sắp xếp:** query param, ví dụ `?category=laptop&min_price=1000000&sort=-created_at`.
- **Vai trò truy cập** ghi ở cột "Auth": `Public` / `Customer` / `Seller` / `Admin` / `Owner` (chủ sở hữu dữ liệu, object-level permission).
- Toàn bộ response theo format `{ success, message, data }` hoặc kèm `errors`/`meta` như đã định nghĩa ở `CODING_STANDARDS.md`.
- Tài liệu OpenAPI/Swagger tự sinh bằng `drf-spectacular` tại `/api/docs/` — tài liệu này là bản thiết kế nguồn, không thay thế Swagger.

---

## 1. Auth & Account (`/api/v1/auth`, `/api/v1/users`)

| Method | Endpoint | Auth | Mô tả | Mã YC |
|---|---|---|---|---|
| POST | `/auth/register` | Public | Đăng ký email + mật khẩu | CUS-01 |
| POST | `/auth/verify-email` | Public | Xác thực email qua token | CUS-01 |
| POST | `/auth/resend-verification` | Public | Gửi lại email xác thực (phản hồi chống dò email) | CUS-01 |
| POST | `/auth/login` | Public | Đăng nhập, trả access; đặt refresh vào cookie HttpOnly | CUS-02 |
| POST | `/auth/session` | Public | Khôi phục phiên từ cookie; trả `data: null` nếu đang là khách | CUS-02 |
| POST | `/auth/refresh` | Public | Làm mới access token | CUS-02 |
| POST | `/auth/logout` | Owner | Thu hồi (blacklist) refresh token | CUS-02 |
| POST | `/auth/google` | Public | Đăng nhập bằng Google id_token | CUS-03 |
| POST | `/auth/forgot-password` | Public | Gửi email đặt lại mật khẩu | CUS-04 |
| POST | `/auth/reset-password` | Public | Đặt mật khẩu mới bằng token | CUS-04 |
| GET | `/users/me` | Owner | Xem hồ sơ cá nhân | CUS-05 |
| PATCH | `/users/me` | Owner | Cập nhật hồ sơ cá nhân | CUS-05 |
| POST | `/users/me/avatar` | Owner | Upload ảnh đại diện JPEG/PNG/WebP, kiểm tra nội dung thật và chuẩn hóa ảnh | CUS-05, NFR-03 |
| POST | `/users/me/change-password` | Owner | Đổi mật khẩu (yêu cầu mật khẩu cũ) | CUS-05 |
| GET | `/users/me/addresses` | Owner | Danh sách địa chỉ | CUS-06 |
| POST | `/users/me/addresses` | Owner | Thêm địa chỉ | CUS-06 |
| PATCH | `/users/me/addresses/{id}` | Owner | Sửa địa chỉ | CUS-06 |
| DELETE | `/users/me/addresses/{id}` | Owner | Xóa địa chỉ | CUS-06 |
| POST | `/users/me/addresses/{id}/set-default` | Owner | Đặt làm địa chỉ mặc định | CUS-06 |

---

## 2. Admin — Quản lý người dùng & Seller (`/api/v1/admin`)

| Method | Endpoint | Auth | Mô tả | Mã YC |
|---|---|---|---|---|
| GET | `/admin/dashboard/summary` | Admin | Thẻ thống kê tổng quan | ADM-01 |
| GET | `/admin/dashboard/revenue-chart` | Admin | Biểu đồ doanh thu theo thời gian | ADM-02 |
| GET | `/admin/dashboard/top-products` | Admin | Top 10 sản phẩm bán chạy | ADM-03 |
| GET | `/admin/customers` | Admin | Danh sách khách hàng (search, filter, phân trang) | ADM-04 |
| GET | `/admin/customers/{id}` | Admin | Chi tiết khách hàng | ADM-04 |
| POST | `/admin/customers` | Admin | Tạo khách hàng | ADM-04 |
| PATCH | `/admin/customers/{id}` | Admin | Cập nhật | ADM-04 |
| DELETE | `/admin/customers/{id}` | Admin | Xóa mềm | ADM-04 |
| GET | `/admin/sellers` | Admin | Danh sách seller (filter theo trạng thái) | ADM-05 |
| GET | `/admin/sellers/{id}` | Admin | Chi tiết seller + shop | ADM-05 |
| PATCH | `/admin/sellers/{id}` | Admin | Sửa thông tin gian hàng | ADM-05 |
| DELETE | `/admin/sellers/{id}` | Admin | Xóa mềm seller và shop, kèm lý do | ADM-05 |
| POST | `/admin/users/{id}/lock` | Admin | Khóa tài khoản (kèm lý do) | ADM-06 |
| POST | `/admin/users/{id}/unlock` | Admin | Mở khóa tài khoản | ADM-06 |
| POST | `/admin/users/{id}/reset-password` | Admin | Reset mật khẩu người dùng | ADM-07 |
| POST | `/admin/users/{id}/assign-role` | Admin | Gán/thu hồi vai trò | ADM-08 |
| GET | `/admin/seller-applications` | Admin | Hàng chờ duyệt đăng ký seller | ADM-09 |
| GET | `/admin/seller-applications/{id}` | Admin | Chi tiết hồ sơ | ADM-09 |
| POST | `/admin/seller-applications/{id}/approve` | Admin | Duyệt hồ sơ seller | ADM-09 |
| POST | `/admin/seller-applications/{id}/reject` | Admin | Từ chối kèm lý do | ADM-09 |
| POST | `/admin/seller-documents/{id}/review` | Admin | Xác minh hoặc yêu cầu bổ sung từng giấy tờ | ADM-10 |
| POST | `/admin/shops/{id}/lock` | Admin | Khóa gian hàng | ADM-11 |
| POST | `/admin/shops/{id}/unlock` | Admin | Mở khóa gian hàng | ADM-11 |
| GET | `/admin/shops/{id}/revenue` | Admin | Doanh thu seller theo tháng | ADM-12 |

Ghi chú hiện thực Nhóm 1:

- Địa chỉ đầu tiên tự trở thành mặc định; khi xóa địa chỉ mặc định, hệ thống chọn một địa chỉ còn hoạt động thay thế. Mọi truy vấn địa chỉ lấy chủ sở hữu từ `request.user`.
- `DELETE /admin/customers/{id}` đặt `is_deleted = TRUE`, `is_active = FALSE`, thu hồi toàn bộ
  JWT và thay email đăng nhập bằng định danh vô hiệu. Bản ghi cũ vẫn được giữ cho audit/lịch sử,
  còn email ban đầu được phép đăng ký lại thành một Customer mới và phải xác thực lại.
- Khóa/mở khóa yêu cầu `reason`, thu hồi phiên hiện tại, ghi `AuditLog` và gửi email bằng Celery.
- Admin reset mật khẩu sẽ vô hiệu mật khẩu cũ, thu hồi phiên, đặt `must_change_password = TRUE` và gửi link token qua email. Cờ được xóa sau khi người dùng đặt mật khẩu mới thành công.
- Duyệt hồ sơ seller chạy trong transaction: chuyển role, tạo Shop có slug duy nhất, thu hồi
  session cũ, tạo Notification/AuditLog và chỉ enqueue email sau commit.
- Giấy tờ lưu dưới private media prefix; API có quyền chỉ trả signed download URL sống 5 phút,
  không trả đường dẫn storage thô.
- `reason` và `request_id` của thao tác khóa/mở/duyệt/từ chối được lưu vào `AuditLog`; log runtime
  có `request_id`, actor `user_id` và target.

## 3. Admin — Quản lý sản phẩm & Danh mục

| Method | Endpoint | Auth | Mô tả | Mã YC |
|---|---|---|---|---|
| GET | `/admin/products/pending` | Admin | Hàng chờ duyệt sản phẩm | ADM-13 |
| POST | `/admin/products/{id}/approve` | Admin | Duyệt sản phẩm | ADM-13 |
| POST | `/admin/products/{id}/reject` | Admin | Từ chối kèm lý do | ADM-13 |
| POST | `/admin/products/{id}/hide` | Admin | Ẩn sản phẩm vi phạm | ADM-14 |
| DELETE | `/admin/products/{id}` | Admin | Xóa mềm sản phẩm vi phạm | ADM-14 |
| GET | `/categories` | Public | Cây danh mục | ADM-15 |
| POST | `/admin/categories` | Admin | Tạo danh mục | ADM-15 |
| PATCH | `/admin/categories/{id}` | Admin | Sửa danh mục | ADM-15 |
| DELETE | `/admin/categories/{id}` | Admin | Xóa danh mục | ADM-15 |
| POST | `/admin/categories/reorder` | Admin | Sắp xếp lại thứ tự (kéo thả) | ADM-15 |
| GET | `/brands` | Public | Danh sách thương hiệu | ADM-16 |
| POST | `/admin/brands` | Admin | Tạo thương hiệu | ADM-16 |
| PATCH | `/admin/brands/{id}` | Admin | Sửa thương hiệu | ADM-16 |
| DELETE | `/admin/brands/{id}` | Admin | Xóa thương hiệu | ADM-16 |

## 4. Admin — Đơn hàng, Khuyến mãi, Báo cáo, Hệ thống

| Method | Endpoint | Auth | Mô tả | Mã YC |
|---|---|---|---|---|
| GET | `/admin/orders` | Admin | Danh sách mọi đơn hàng (filter đa điều kiện) | ADM-17 |
| GET | `/admin/orders/{id}` | Admin | Chi tiết đơn + timeline | ADM-17 |
| GET | `/admin/disputes` | Admin | Danh sách tranh chấp | ADM-18 |
| GET | `/admin/disputes/{id}` | Admin | Chi tiết tranh chấp + chứng cứ | ADM-18 |
| POST | `/admin/disputes/{id}/resolve` | Admin | Ra quyết định (hoàn/từ chối/hoàn 1 phần) | ADM-18 |
| GET/POST | `/admin/flash-sales` | Admin | Danh sách / tạo Flash Sale | ADM-19 |
| PATCH/DELETE | `/admin/flash-sales/{id}` | Admin | Sửa / xóa Flash Sale | ADM-19 |
| GET/POST | `/admin/coupons` | Admin | Danh sách / tạo coupon cấp sàn | ADM-20 |
| PATCH/DELETE | `/admin/coupons/{id}` | Admin | Sửa / xóa coupon | ADM-20 |
| GET/POST | `/admin/banners` | Admin | Danh sách / tạo banner | ADM-21 |
| PATCH/DELETE | `/admin/banners/{id}` | Admin | Sửa / xóa banner | ADM-21 |
| POST | `/admin/banners/reorder` | Admin | Sắp xếp lại thứ tự | ADM-21 |
| GET | `/admin/reports/top-sellers` | Admin | Top seller theo doanh thu | ADM-22 |
| GET | `/admin/reports/top-customers` | Admin | Top khách hàng theo chi tiêu | ADM-22 |
| GET | `/admin/reports/top-categories` | Admin | Top danh mục theo số lượng bán | ADM-22 |
| GET | `/admin/reports/cancel-return-rate` | Admin | Tỷ lệ hoàn/hủy đơn | ADM-23 |
| POST | `/admin/reports/export` | Admin | Xuất báo cáo Excel/PDF (job nền) | ADM-24 |
| GET | `/admin/audit-logs` | Admin | Tra cứu Audit Log (filter) | ADM-25 |
| GET | `/admin/settings` | Admin | Xem cấu hình hệ thống | ADM-26 |
| PUT | `/admin/settings` | Admin | Cập nhật cấu hình hệ thống | ADM-26 |

---

## 5. Seller — Dashboard, Sản phẩm, Kho (`/api/v1/seller`)

Toàn bộ endpoint dưới đây tự động scope theo `shop_id` của Seller đang đăng nhập (BR-SHOP-04) — không có tham số `shop_id` trên URL.

| Method | Endpoint | Auth | Mô tả | Mã YC |
|---|---|---|---|---|
| GET | `/seller/dashboard/summary` | Seller | Thẻ thống kê gian hàng | SEL-01 |
| GET | `/seller/dashboard/revenue-chart` | Seller | Biểu đồ doanh thu 30 ngày | SEL-01 |
| GET | `/seller/products` | Seller | Danh sách sản phẩm shop (search, filter) | SEL-02 |
| POST | `/seller/products` | Seller | Tạo sản phẩm (trạng thái draft) | SEL-02 |
| GET | `/seller/products/{id}` | Seller | Chi tiết sản phẩm | SEL-02 |
| PATCH | `/seller/products/{id}` | Seller | Cập nhật sản phẩm | SEL-02 |
| DELETE | `/seller/products/{id}` | Seller | Xóa mềm | SEL-02 |
| POST | `/seller/products/{id}/submit` | Seller | Gửi duyệt (draft → pending) | SEL-02 |
| POST | `/seller/products/{id}/media` | Seller | Upload ảnh/video | SEL-03 |
| DELETE | `/seller/products/{id}/media/{media_id}` | Seller | Xóa 1 media | SEL-03 |
| POST | `/seller/products/{id}/media/reorder` | Seller | Sắp xếp lại thứ tự ảnh | SEL-03 |
| GET | `/seller/attributes` | Seller | Danh sách thuộc tính khả dụng | SEL-04 |
| POST | `/seller/products/{id}/variants/generate` | Seller | Sinh tổ hợp biến thể từ thuộc tính | SEL-04 |
| PATCH | `/seller/products/{id}/variants/{variant_id}` | Seller | Sửa 1 biến thể (giá, SKU, tồn kho ban đầu) | SEL-04..05 |
| GET | `/seller/inventory/stock-entries` | Seller | Danh sách phiếu nhập/xuất | SEL-06..07 |
| POST | `/seller/inventory/stock-entries` | Seller | Tạo phiếu nhập/xuất/điều chỉnh | SEL-06..07 |
| POST | `/seller/inventory/stock-entries/{id}/confirm` | Seller | Xác nhận phiếu (cộng/trừ tồn kho) | SEL-06..07 |
| GET | `/seller/inventory/movements` | Seller | Lịch sử biến động tồn kho (theo variant) | SEL-08 |
| GET | `/seller/inventory/low-stock` | Seller | Danh sách sản phẩm sắp hết hàng | SEL-09 |
| PATCH | `/seller/products/{id}/variants/{variant_id}/threshold` | Seller | Đặt ngưỡng cảnh báo tồn kho | SEL-09 |

## 6. Seller — Đơn hàng, Voucher, Khách hàng, Đánh giá, Chat, Shop

| Method | Endpoint | Auth | Mô tả | Mã YC |
|---|---|---|---|---|
| GET | `/seller/orders` | Seller | Danh sách đơn của shop (filter status) | SEL-10 |
| GET | `/seller/orders/{id}` | Seller | Chi tiết đơn | SEL-10 |
| POST | `/seller/orders/{id}/confirm` | Seller | Xác nhận đơn | SEL-10 |
| POST | `/seller/orders/{id}/pack` | Seller | Chuyển "Đang đóng gói" | SEL-10 |
| POST | `/seller/orders/{id}/ship` | Seller | Chuyển "Đang giao" | SEL-10 |
| POST | `/seller/orders/{id}/complete` | Seller | Chuyển "Hoàn thành" | SEL-10 |
| POST | `/seller/orders/{id}/cancel` | Seller | Hủy đơn (kèm lý do) | SEL-10 |
| GET | `/seller/orders/{id}/packing-slip` | Seller | In phiếu giao/đóng gói (PDF) | SEL-11 |
| GET/POST | `/seller/coupons` | Seller | Danh sách / tạo voucher shop | SEL-12 |
| PATCH/DELETE | `/seller/coupons/{id}` | Seller | Sửa / xóa voucher shop | SEL-12 |
| GET | `/seller/customers` | Seller | Danh sách khách đã mua tại shop | SEL-13 |
| GET | `/seller/customers/{id}/orders` | Seller | Lịch sử mua của 1 khách | SEL-13 |
| GET | `/seller/reviews` | Seller | Danh sách đánh giá của shop | SEL-14 |
| POST | `/seller/reviews/{id}/reply` | Seller | Trả lời đánh giá | SEL-14 |
| POST | `/seller/reviews/{id}/report` | Seller | Báo cáo review vi phạm | SEL-15 |
| GET | `/seller/conversations` | Seller | Danh sách hội thoại | SEL-16 |
| GET | `/seller/conversations/{id}/messages` | Seller | Lịch sử tin nhắn | SEL-16 |
| WS | `/ws/chat/{conversation_id}` | Seller/Customer | Kênh chat realtime | SEL-16, CUS-20 |
| GET | `/shops/{slug}` | Public | Info shop + danh sách sản phẩm phân trang trong một response | SEL-17 |
| POST | `/seller-applications/me` | Owner (Customer) | Bước 1: nộp thông tin đăng ký seller | SEL-18 |
| GET | `/seller-applications/me` | Owner | Theo dõi trạng thái hồ sơ của chính user | SEL-18 |
| POST | `/seller-applications/me/documents` | Owner (Customer) | Bước 2: upload JPEG/PNG/PDF | SEL-18 |
| GET | `/seller/shop` | Seller/Owner | Lấy shop từ JWT, không nhận `shop_id` client | SEL-17, NFR-02 |
| PATCH | `/seller/shop` | Seller/Owner | Cập nhật shop của chính seller | SEL-17, NFR-02 |
| POST | `/seller/shop/logo` | Seller/Owner | Upload JPEG/PNG/WebP; crop và lưu WebP 512×512 | SEL-17 |
| POST | `/seller/shop/cover` | Seller/Owner | Upload JPEG/PNG/WebP; crop và lưu WebP 1600×480 | SEL-17 |
| GET/PATCH | `/seller/shops/{id}` | Seller/Owner | Endpoint kiểm tra object-level; ID vẫn bị scope theo owner | NFR-02 |

Ghi chú SEL-17/ADM-11 trong Sprint 2:

- Do Product chưa có model, public shop trả `products: []`, `available_filters`,
  `available_sorts` và `meta` đúng contract để Sprint 3 nối selector thật.
- Public selector chỉ trả Shop `approved`; Shop `locked` nhận 404.
- `ShopBusinessPolicy.ensure_can_create_new_resource()` là contract bắt buộc cho service tạo
  Product/Order mới. Xử lý order đã tồn tại không dùng policy này, nên vẫn hoạt động khi shop khóa.
- `PATCH /seller/shop` không nhận `logo_url`/`cover_url`; ảnh phải đi qua hai endpoint multipart để
  backend xác minh nội dung, chuẩn hóa kích thước và tránh hotlink ảnh ngoài.

---

## 7. Customer — Trang chủ, Tìm kiếm, Sản phẩm (Public)

| Method | Endpoint | Auth | Mô tả | Mã YC |
|---|---|---|---|---|
| GET | `/home` | Public | API tổng hợp trang chủ (banner, Flash Sale, gợi ý, mới/bán chạy) | CUS-07 |
| GET | `/search/suggestions` | Public | Autocomplete từ khóa | CUS-08 |
| GET | `/search` | Public | Kết quả tìm kiếm (phân trang) | CUS-08 |
| GET | `/products` | Public | Danh sách sản phẩm + bộ lọc đa tiêu chí | CUS-09 |
| GET | `/products/{slug}` | Public | Chi tiết sản phẩm (kèm variants, media) | CUS-10 |
| GET | `/products/{id}/reviews` | Public | Đánh giá sản phẩm (lọc theo sao/ảnh) | CUS-11 |
| GET | `/products/{id}/questions` | Public | Danh sách Q&A | CUS-11 |
| POST | `/products/{id}/questions` | Owner (Customer) | Đặt câu hỏi | CUS-11 |
| POST | `/questions/{id}/answers` | Seller | Trả lời câu hỏi | CUS-11 |

## 8. Customer — Wishlist, Giỏ hàng, Checkout, Thanh toán

| Method | Endpoint | Auth | Mô tả | Mã YC |
|---|---|---|---|---|
| GET | `/wishlist` | Owner | Danh sách yêu thích | CUS-12 |
| POST | `/wishlist/toggle` | Owner | Thêm/bỏ yêu thích | CUS-12 |
| GET | `/cart` | Owner | Xem giỏ hàng | CUS-13 |
| POST | `/cart/items` | Owner | Thêm sản phẩm vào giỏ | CUS-13 |
| PATCH | `/cart/items/{id}` | Owner | Sửa số lượng / trạng thái chọn | CUS-13 |
| DELETE | `/cart/items/{id}` | Owner | Xóa 1 dòng khỏi giỏ | CUS-13 |
| POST | `/cart/merge` | Owner | Merge giỏ localStorage vào giỏ DB khi đăng nhập | CUS-13 |
| POST | `/checkout/preview` | Owner | Xem trước tổng tiền (kiểm tra tồn kho, voucher, phí ship) | CUS-14 |
| POST | `/checkout/confirm` | Owner | Xác nhận đặt hàng — tạo Order theo từng shop | CUS-14 |
| GET | `/payment-methods` | Public | Danh sách phương thức thanh toán khả dụng | CUS-15 |
| POST | `/payment/{order_id}/initiate` | Owner | Khởi tạo giao dịch với cổng thanh toán, trả URL redirect | CUS-15 |
| POST | `/payment/callback/{gateway}` | Public (server-to-server) | Nhận callback/IPN từ cổng thanh toán | CUS-15 |
| GET | `/payment/{order_id}/status` | Owner | Kiểm tra trạng thái thanh toán | CUS-15 |

## 9. Customer — Đơn hàng, Đánh giá, Thông báo

| Method | Endpoint | Auth | Mô tả | Mã YC |
|---|---|---|---|---|
| GET | `/orders` | Owner | Danh sách đơn của tôi (tab theo trạng thái) | CUS-16 |
| GET | `/orders/{id}` | Owner | Chi tiết đơn + timeline | CUS-16 |
| POST | `/orders/{id}/cancel` | Owner | Hủy đơn (khi chưa xác nhận) | CUS-17 |
| POST | `/orders/{id}/reorder` | Owner | Mua lại — thêm toàn bộ item vào giỏ | CUS-17 |
| POST | `/orders/{id}/return-request` | Owner | Mở yêu cầu trả hàng/hoàn tiền | CUS-18 |
| GET | `/orders/{id}/return-request` | Owner | Xem trạng thái yêu cầu trả hàng | CUS-18 |
| POST | `/order-items/{id}/review` | Owner | Viết đánh giá sản phẩm đã mua | CUS-19 |
| PATCH | `/reviews/{id}` | Owner | Sửa đánh giá (trong 7 ngày) | CUS-19 |
| GET | `/conversations` | Owner | Danh sách hội thoại của tôi | CUS-20 |
| GET | `/notifications` | Owner | Trung tâm thông báo | CUS-21 |
| POST | `/notifications/{id}/read` | Owner | Đánh dấu đã đọc | CUS-21 |
| POST | `/notifications/read-all` | Owner | Đánh dấu tất cả đã đọc | CUS-21 |
| WS | `/ws/notifications` | Owner | Kênh đẩy thông báo realtime | CUS-21, BON-08 |

---

## 10. AI Service (`/api/v1/ai`)

Toàn bộ endpoint dưới đây được xử lý bởi `AIService` (xem `ARCHITECTURE.md` mục 6) — request/response ở đây là hợp đồng công khai, còn việc gọi provider nào là chi tiết ẩn bên trong.

| Method | Endpoint | Auth | Mô tả | Mã YC |
|---|---|---|---|---|
| GET | `/ai/smart-search` | Public | Tìm kiếm theo nhu cầu tự nhiên | AI-01 |
| GET | `/ai/semantic-search` | Public | Semantic search bằng embeddings | AI-02 |
| GET | `/products/{id}/recommendations` | Public/Owner | Gợi ý cá nhân hóa ("Gợi ý cho bạn") | AI-03 |
| GET | `/products/{id}/similar` | Public | Sản phẩm tương tự | AI-04 |
| POST | `/ai/assistant/chat` | Owner (Customer) | Gửi tin nhắn tới AI Shopping Assistant (stream SSE/WS) | AI-05 |
| POST | `/ai/support/auto-reply` | Hệ thống (nội bộ, gọi từ Chat module) | Tự động trả lời câu hỏi phổ biến trong chat | AI-06 |
| GET | `/products/{id}/ai-review-summary` | Public | Tóm tắt AI từ toàn bộ đánh giá | AI-07 |
| GET | `/products/{id}/ai-summary` | Public | Tóm tắt nhanh mô tả sản phẩm | AI-08 |
| POST | `/ai/compare` | Public | So sánh 2-4 sản phẩm | AI-09 |
| POST | `/seller/ai/generate-description` | Seller | Sinh tiêu đề/mô tả/SEO cho sản phẩm | AI-10 |
| POST | `/seller/ai/auto-tag` | Seller | Đề xuất tag/danh mục/từ khóa | AI-11 |
| POST | `/seller/products/{id}/ai/translate` | Seller | Dịch mô tả sản phẩm | AI-12 |
| GET | `/seller/products/{id}/ai/price-suggestion` | Seller | Đề xuất khoảng giá bán | AI-13 |
| GET | `/admin/ai/sales-analytics` | Admin | Nhận định AI trên dashboard Admin | AI-14 |
| GET | `/seller/ai/sales-analytics` | Seller | Nhận định AI trên dashboard Seller | AI-14 |

---

## 11. Bonus Features

| Method | Endpoint | Auth | Mô tả | Mã YC |
|---|---|---|---|---|
| GET | `/orders/{id}/tracking` | Owner | Timeline vận chuyển chi tiết | BON-01 |
| POST | `/shops/{id}/follow` | Owner | Theo dõi / bỏ theo dõi shop | BON-02 |
| GET/POST | `/seller/bundles` | Seller | Danh sách / tạo combo sản phẩm | BON-03 |
| GET | `/products/{id}/add-on-deals` | Public | Gợi ý mua kèm giảm giá | BON-04 |
| GET | `/affiliate/my-links` | Owner | Link giới thiệu & thống kê hoa hồng | BON-05 |
| GET | `/loyalty/points` | Owner | Lịch sử tích/tiêu điểm thưởng | BON-06 |
| GET | `/wallet` | Owner | Số dư & lịch sử giao dịch ví | BON-07 |
| POST | `/products/{id}/notify-when-available` | Owner | Đăng ký waitlist hết hàng | BON-09 |
| POST | `/reports` | Owner | Báo cáo vi phạm (sản phẩm/review/shop) | BON-10 |
| GET | `/admin/reports` | Admin | Hàng chờ xử lý báo cáo vi phạm | BON-10 |
| POST | `/seller/products/import` | Seller | Import sản phẩm hàng loạt từ Excel | BON-11 |
| GET | `/seller/products/export` | Seller | Export danh sách sản phẩm | BON-11 |
| GET | `/seller/orders/export` | Seller | Export danh sách đơn hàng | BON-11 |
| GET | `/orders/{id}/qrcode` | Owner | QR tra cứu đơn hàng | BON-12 |
| GET | `/products/{id}/qrcode` | Public | QR dẫn tới trang chi tiết sản phẩm | BON-12 |
| GET | `/products/trending` | Public | Sản phẩm đang thịnh hành | BON-13 |
| WS | `/ws/flash-sale/{id}` | Public | Cập nhật số lượng còn lại realtime | BON-14 |

---

## 12. Ví dụ Request/Response chi tiết

### `POST /checkout/confirm`

**Request:**
```json
{
    "address_id": 12,
    "payment_method": "vnpay",
    "coupons": {
        "platform": "SALE50K",
        "shop_1": "SHOP10"
    }
}
```

**Response (thành công — 1 giỏ có 2 shop → 2 order):**
```json
{
    "success": true,
    "message": "Đặt hàng thành công",
    "data": {
        "orders": [
            { "order_id": 1001, "order_code": "ORD-20260721-0001", "shop_id": 1, "total_amount": 1250000 },
            { "order_id": 1002, "order_code": "ORD-20260721-0002", "shop_id": 2, "total_amount": 480000 }
        ],
        "payment_redirect_url": "https://sandbox.vnpayment.vn/..."
    }
}
```

**Response (lỗi — item hết hàng, theo BR-CART-04):**
```json
{
    "success": false,
    "message": "Một số sản phẩm trong giỏ đã hết hàng",
    "errors": {
        "cart_items": [
            { "variant_id": 55, "reason": "out_of_stock", "available_quantity": 0 }
        ]
    }
}
```

### `GET /products?category=laptop&min_price=10000000&max_price=25000000&sort=-sold_count&page=1`

**Response:**
```json
{
    "success": true,
    "message": "Lấy danh sách sản phẩm thành công",
    "data": [
        { "id": 501, "name": "Laptop ABC 15\"", "slug": "laptop-abc-15", "price": 18990000, "avg_rating": 4.6, "sold_count": 320 }
    ],
    "meta": { "page": 1, "page_size": 20, "total_items": 87, "total_pages": 5 }
}
```

---

## 13. Ghi chú thiết kế quan trọng

- **Checkout tách đơn theo shop** (BR-CART-02) → `POST /checkout/confirm` trả về **mảng** order, không phải 1 order duy nhất.
- **Payment callback** (`/payment/callback/{gateway}`) là endpoint duy nhất được phép public nhưng không dùng JWT — xác thực bằng chữ ký của cổng thanh toán; phải idempotent (BR-PAY-01).
- **Mọi endpoint dưới `/seller/*`** tự động scope theo shop của Seller đang đăng nhập ở tầng Service/Repository — không có và không được thêm tham số `shop_id` trên URL hay body (BR-SHOP-04).
- **Mọi endpoint dưới `/admin/*`** yêu cầu role Admin; hành động thay đổi trạng thái (lock, approve, resolve...) đều ghi Audit Log (BR-SEC-02).
- Các endpoint AI (`/ai/*`) nên có timeout ngắn ở tầng gateway/Nginx và luôn có phản hồi fallback nếu AIService lỗi (BR-AI-05) — không để request treo.

## 14. Tài liệu liên quan

- `database_design.md` — cấu trúc dữ liệu đứng sau các endpoint này.
- `business_rules.md` — quy tắc nghiệp vụ áp dụng khi validate request.
- `workflows.md` — trình tự gọi API tương ứng với từng luồng nhiều bước (checkout, order status, return/dispute...).
- `CODING_STANDARDS.md` — quy chuẩn chung về REST, response format, error handling.
- `roles.md` — chi tiết quyền hạn đứng sau cột "Auth" ở các bảng trên.
