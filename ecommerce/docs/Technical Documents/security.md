# Security

Tài liệu tổng hợp toàn bộ yêu cầu bảo mật của hệ thống, mở rộng từ `NFR-01..04` và `BR-SEC-*` trong đặc tả và `business_rules.md`. Đây là tài liệu tham chiếu khi review code liên quan tới bảo mật — mỗi mục có checklist cụ thể.

---

## 1. Xác thực (Authentication)

**Yêu cầu:** NFR-01, CUS-01..04.

- JWT access token thời hạn ngắn (khuyến nghị 15 phút) + refresh token thời hạn dài hơn (khuyến nghị 7 ngày).
- Refresh token **rotation**: mỗi lần refresh sinh token mới, token cũ bị vô hiệu (`ROTATE_REFRESH_TOKENS = True` với `djangorestframework-simplejwt`).
- **Blacklist** refresh token khi logout hoặc khi tài khoản bị khóa — token cũ không dùng lại được dù chưa hết hạn.
- Mật khẩu hash bằng thuật toán mạnh (PBKDF2 mặc định của Django, hoặc Argon2 — khuyến nghị nâng cấp).
- Access token lưu ở FE trong memory (Pinia store), **không** lưu ở `localStorage` (tránh XSS đánh cắp token). Refresh token qua `httpOnly` cookie là điểm cộng an toàn hơn.
- Không truyền token qua query string URL (tránh lộ trong log truy cập/lịch sử trình duyệt).
- Đăng nhập sai quá N lần trong khoảng thời gian → rate limit tạm thời (không khóa vĩnh viễn) — BR-ACC-03.
- Google Login: verify `id_token` ở Backend bằng thư viện chính thức của Google, không tin token thô từ FE gửi lên mà không verify.

**Checklist review code:**
- [ ] Endpoint đăng nhập/đăng ký có rate limit chưa?
- [ ] Token access không bị log ra console/log file?
- [ ] Logout có blacklist refresh token không?

---

## 2. Phân quyền (Authorization)

**Yêu cầu:** NFR-02, ADM-08.

- Mọi API endpoint khai báo `permission_classes` rõ ràng — không có endpoint "mặc định cho phép mọi role" bởi thiếu khai báo.
- **Role-based**: dùng permission class riêng cho từng role (`IsAdmin`, `IsSeller`, `IsCustomer`).
- **Object-level permission** (quan trọng hơn role-based trong hệ marketplace): kiểm tra người dùng có quyền trên **chính đối tượng** đang thao tác, không chỉ đúng role.
  - Seller chỉ sửa được sản phẩm/đơn hàng/kho thuộc shop của mình (BR-SHOP-04).
  - Customer chỉ xem/sửa được đơn hàng, địa chỉ, review của chính mình.
- **Không bao giờ tin ID từ client** để xác định quyền sở hữu — `shop_id`, `user_id` luôn lấy từ `request.user`, không lấy từ body/query param của request (BR-SEC-01). Xem code mẫu ở `coding_patterns.md` mục 3.
- Test phân quyền bắt buộc cho các API nhạy cảm: thử truy cập dữ liệu người khác bằng cách đổi ID trên URL — phải trả 403/404, không trả về dữ liệu.

**Checklist review code:**
- [ ] Mọi ViewSet có `permission_classes` tường minh?
- [ ] Có test case "user A không đọc/sửa được dữ liệu user B"?
- [ ] Queryset trong `get_queryset()` có scope theo `request.user` không?

---

## 3. Chống tấn công phổ biến

**Yêu cầu:** NFR-03.

### 3.1 SQL Injection
- Luôn dùng Django ORM/QuerySet; không nối chuỗi SQL thô. Nếu bắt buộc dùng raw SQL, dùng parameterized query (`cursor.execute(sql, params)`), không f-string nối giá trị người dùng vào SQL.

### 3.2 XSS (Cross-Site Scripting)
- Mô tả sản phẩm/rich-text (SEL-02) phải sanitize bằng `bleach` hoặc `nh3` trước khi lưu — loại bỏ thẻ `<script>`, event handler (`onerror`, `onclick`...), chỉ giữ whitelist thẻ an toàn (`<p>`, `<b>`, `<img>` với `src` được validate...).
- Vue tự động escape nội dung trong template (`{{ }}`) — **không dùng `v-html`** với nội dung do người dùng nhập trực tiếp mà chưa qua sanitize ở Backend.

### 3.3 CSRF
- API dùng JWT Bearer token (không dựa vào session cookie) nên ít rủi ro CSRF hơn form truyền thống; vẫn cần bật CSRF protection cho các endpoint dùng cookie (nếu áp dụng `httpOnly` cookie cho refresh token).

### 3.4 Rate Limiting
- Áp dụng cho: đăng nhập, đăng ký, quên mật khẩu, OTP (nếu có), endpoint AI (chống lạm dụng chi phí).
- Dùng `django-ratelimit` hoặc rate limit ở tầng Nginx cho các endpoint công khai dễ bị abuse.

### 3.5 File Upload
- Kiểm tra **content-type thật** của file (đọc magic bytes), không chỉ dựa vào phần đuôi mở rộng (`.jpg`, `.png`...) — BR-SEC-03.
- Giới hạn dung lượng file (ảnh sản phẩm, giấy tờ seller, ảnh review, ảnh chat).
- Giới hạn định dạng cho phép theo từng loại upload (ảnh: jpg/png/webp; giấy tờ: pdf/jpg/png).
- Ảnh upload nên qua xử lý lại (resize, strip EXIF metadata có thể chứa thông tin nhạy cảm như GPS) trước khi lưu.
- Lưu file ở storage riêng (không chung thư mục với code); không cho phép truy cập trực tiếp thư mục upload thực thi được (`X-Content-Type-Options: nosniff`).

### 3.6 Ẩn thông tin lỗi ở Production
- Ở production (`DEBUG = False`), không trả traceback, câu SQL lỗi, hay đường dẫn file nội bộ ra response — dùng exception handler chung (xem `coding_patterns.md` mục 6) trả `message` chung chung, chi tiết lỗi chỉ ghi vào log nội bộ.

**Checklist review code:**
- [ ] Nội dung rich-text có qua sanitize trước khi lưu DB không?
- [ ] Upload file có kiểm tra content-type thật, không chỉ đuôi file?
- [ ] `DEBUG = False` ở môi trường production, `ALLOWED_HOSTS` được cấu hình đúng?

---

## 4. Quản lý Secrets

**Yêu cầu:** NFR-04.

- Toàn bộ secrets (DB password, `JWT_SECRET_KEY`, AI API key, payment gateway key) đọc từ biến môi trường (`django-environ`), **không hardcode** trong code.
- File `.env` **không commit** vào Git — có `.gitignore` chặn, và `.env.example` liệt kê đầy đủ tên biến (không có giá trị thật) để người khác biết cần cấu hình gì.
- Secrets khác nhau giữa môi trường dev/staging/production — không dùng chung 1 bộ key.
- Khuyến khích chạy `gitleaks` hoặc công cụ tương tự trong CI để phát hiện secret bị commit nhầm (điểm cộng theo NFR-04).
- Xoay vòng (rotate) `JWT_SECRET_KEY` và API key định kỳ hoặc ngay khi nghi ngờ rò rỉ.

**Checklist review code:**
- [ ] Không có secret nào hardcode trong code hay trong `docker-compose.yml`?
- [ ] `.env.example` có cập nhật khi thêm biến môi trường mới?

---

## 5. Bảo mật đặc thù cho hệ thống Multi-vendor

Bổ sung ngoài các mục chuẩn ở trên — đây là nhóm rủi ro riêng của mô hình marketplace (xem thêm `PROJECT_CONSTITUTION.md` mục 14, `business_rules.md` mục 2).

- **Data isolation giữa các Seller** là ưu tiên bảo mật hàng đầu, không kém authentication. Một lỗi cho phép Seller A đọc đơn hàng/khách hàng của Seller B là lỗi nghiêm trọng (data breach), không chỉ là bug thường.
- Viết test tự động riêng cho isolation: đăng nhập Seller A, thử truy cập resource của Seller B qua mọi endpoint `/seller/*` bằng cách đổi ID — phải luôn bị chặn.
- Trang gian hàng công khai (`/shops/{slug}`) chỉ lộ thông tin công khai (tên, logo, sản phẩm, đánh giá), tuyệt đối không lộ dữ liệu nội bộ (doanh thu, thông tin khách hàng, giấy tờ xác minh).

---

## 6. Bảo mật thanh toán

**Yêu cầu:** CUS-15, BR-PAY-01..03.

- Không tự tin trạng thái thanh toán do FE báo về — trạng thái thật lấy từ callback/IPN của cổng thanh toán (server-to-server), có xác thực chữ ký.
- Endpoint callback **idempotent** (BR-PAY-01) — chống replay attack vô tình cộng/trừ tiền nhiều lần.
- Verify chữ ký (checksum/signature) của mọi callback theo đúng thuật toán cổng thanh toán yêu cầu — từ chối callback không hợp lệ, ghi log cảnh báo bảo mật (không xử lý âm thầm).
- Không log toàn bộ thông tin thẻ/tài khoản nhạy cảm nếu cổng thanh toán có gửi kèm (hầu hết cổng sandbox VN không gửi số thẻ thô, nhưng vẫn cần rà soát payload trước khi log).

---

## 7. Bảo mật liên quan tới AI

**Yêu cầu:** AI-15, BR-AI-01..05.

- **Prompt injection**: dữ liệu người dùng nhập (câu hỏi chatbot, tên sản phẩm khi generate description) được đưa vào prompt — cần tách rõ vai trò `system` prompt (chứa chỉ dẫn, không đổi được) và `user` prompt (nội dung người dùng, coi là không tin cậy). Không để nội dung người dùng có thể "ghi đè" chỉ dẫn hệ thống của chatbot (ví dụ chatbot bị dụ tiết lộ giá vốn, dữ liệu nội bộ).
- **Giới hạn phạm vi công cụ (tool use)** của AI Shopping Assistant: chỉ được gọi các tool đọc dữ liệu công khai (`search_products`, `get_product`, `get_policy`) — không cấp cho AI quyền tạo/sửa/xóa dữ liệu trực tiếp.
- **Rate limit riêng cho các endpoint AI** để tránh bị lạm dụng gây tốn chi phí API (đếm theo user, theo IP).
- **Không log dữ liệu nhạy cảm** vào `AIRequestLog` nếu prompt vô tình chứa thông tin cá nhân không cần thiết — rà soát trước khi đưa dữ liệu người dùng vào prompt.
- API key của AI provider quản lý như mọi secret khác (mục 4).

---

## 8. Logging & Giám sát bảo mật

**Yêu cầu:** NFR-15.

- Log có cấu trúc, gắn `request_id` để truy vết một request end-to-end.
- Log riêng, dễ tra cứu cho: lỗi thanh toán, lỗi AI provider, các lần đăng nhập thất bại liên tiếp, hành động Admin nhạy cảm (đã có Audit Log riêng — mục 9).
- Không log mật khẩu, token, hay nội dung nhạy cảm dưới dạng plaintext.
- Sentry (hoặc công cụ tương tự) để theo dõi lỗi runtime ở production — điểm cộng theo NFR-15.

---

## 9. Audit Log

**Yêu cầu:** ADM-25, BR-SEC-02.

Hành động **bắt buộc** ghi Audit Log, không có ngoại lệ:
- Khóa/mở khóa tài khoản người dùng
- Duyệt/từ chối hồ sơ Seller
- Khóa/mở khóa gian hàng
- Sửa/xóa sản phẩm của người khác (Admin can thiệp vào sản phẩm Seller)
- Đổi vai trò/quyền của tài khoản
- Ra quyết định xử lý Dispute

Mỗi bản ghi Audit Log gồm: ai thực hiện (`actor_id`), hành động gì (`action`), trên đối tượng nào (`target_type`, `target_id`), dữ liệu trước/sau (`diff`), thời điểm. Chỉ Admin đọc được Audit Log.

---

## 10. Bảo mật khi triển khai (Docker/Nginx)

**Yêu cầu:** NFR-11..12.

- Container chạy với user không phải root khi có thể.
- `client_max_body_size` ở Nginx giới hạn kích thước upload hợp lý (tránh DoS qua upload file khổng lồ).
- Chỉ mở port cần thiết ra ngoài; PostgreSQL/Redis không expose public.
- Healthcheck từng service để phát hiện sớm service bất thường (có thể là dấu hiệu bị tấn công).
- HTTPS bắt buộc ở môi trường production (khuyến nghị, dù đặc tả tập trung vào môi trường demo/đồ án).

---

## 11. Security Checklist tổng hợp (trước khi release)

- [ ] JWT rotation + blacklist hoạt động đúng
- [ ] Toàn bộ endpoint có `permission_classes` tường minh
- [ ] Test isolation multi-tenant pass (Seller A không đọc được dữ liệu Seller B)
- [ ] Rich-text sanitize trước khi lưu, không có `v-html` với dữ liệu chưa sanitize
- [ ] Rate limit cho login, register, forgot-password, AI endpoints
- [ ] File upload validate content-type thật + giới hạn dung lượng
- [ ] `DEBUG = False`, `.env` không commit, secrets qua biến môi trường
- [ ] Payment callback verify chữ ký + idempotent
- [ ] AI system prompt tách biệt khỏi user input, AI tool chỉ đọc dữ liệu công khai
- [ ] Audit Log ghi đủ cho các hành động nhạy cảm
- [ ] Log không chứa mật khẩu/token plaintext

## 12. Tài liệu liên quan

- `business_rules.md` mục 12 — các rule bảo mật cấp nghiệp vụ (`BR-SEC-*`).
- `PROJECT_CONSTITUTION.md` mục 14–15, 22 — nguyên tắc nền tảng về bảo mật & multi-tenant.
- `coding_patterns.md` mục 3 — code mẫu hiện thực object-level permission.
- `testing_strategy.md` — cách viết test cho các mục Authorization/Isolation ở trên.
- `ARCHITECTURE.md` mục 8–9 — kiến trúc multi-tenant và deployment liên quan.
