# Decision Log

Nhật ký quyết định kiến trúc/kỹ thuật của dự án. Gồm 3 phần: (A) quyết định **đã chốt sẵn** trong tài liệu gốc — coi như ràng buộc bắt buộc; (B) quyết định **"chọn 1" còn tồn đọng** — phải chốt trước khi code phần liên quan; (C) template để ghi quyết định mới phát sinh trong quá trình phát triển.

---

## Phần A — Quyết định đã chốt (ràng buộc bắt buộc)

Các mục dưới đây **không phải chỗ để tranh luận lại** trừ khi có lý do kỹ thuật rất mạnh — chúng đến từ `PROJECT_CONSTITUTION.md` và đã là hợp đồng của dự án. Nếu cần đổi, phải ghi một entry mới ở Phần C giải thích lý do và tác động.

| # | Quyết định | Lý do | Nguồn |
|---|---|---|---|
| A1 | Kiến trúc phân lớp: Presentation → Application → Domain → Infrastructure | Tách business logic khỏi View/Component, dễ bảo trì/test | `PROJECT_CONSTITUTION.md` §3, `ARCHITECTURE.md` §1 |
| A2 | Backend: mỗi module nghiệp vụ = 1 Django app độc lập, cấu trúc `models/serializers/views/services/repositories/...` | Chuẩn hóa cấu trúc, dễ định vị code | `ARCHITECTURE.md` §2 |
| A3 | Frontend: tổ chức theo domain (`features/`), không theo loại file | Khớp NFR-09, dễ mở rộng theo tính năng | `PROJECT_CONSTITUTION.md` §5 |
| A4 | Component không gọi axios trực tiếp — luôn qua `api.ts` của feature | Tách tầng gọi API, dễ mock test | `CODING_STANDARDS.md` §9 |
| A5 | State dùng chung qua Pinia store, không prop-drilling | Tránh truyền props nhiều tầng | `ARCHITECTURE.md` §3 |
| A6 | Response format API thống nhất `{success, message, data[, errors, meta]}` | Đồng bộ FE/BE, dễ xử lý lỗi tập trung | `CODING_STANDARDS.md` §4 |
| A7 | RESTful, đặt tên theo tài nguyên, versioned `/api/v1/` | Chuẩn REST, không RPC-style (`/getProducts`) | `CODING_STANDARDS.md` §3 |
| A8 | Tồn kho/số dư/điểm thưởng: bắt buộc `transaction.atomic()` + `select_for_update()`/`F()`, qua 1 service duy nhất, log append-only | Rủi ro race condition cao nhất hệ thống (oversell) | `PROJECT_CONSTITUTION.md` §8 |
| A9 | Multi-tenant: mọi query Seller lọc theo `shop_id` từ `request.user`, không tin tham số từ client | Lỗ hổng phổ biến nhất của marketplace (Seller A đọc dữ liệu Seller B) | `PROJECT_CONSTITUTION.md` §14 |
| A10 | AI: không gọi thẳng provider — luôn qua `AIService` provider-agnostic | Đổi provider không ảnh hưởng code gọi | `PROJECT_CONSTITUTION.md` §7 |
| A11 | AI Sales Analytics: tính số bằng SQL trước, LLM chỉ diễn giải | Tránh LLM "bịa" số liệu | `PROJECT_CONSTITUTION.md` §7 |
| A12 | Soft delete chuẩn hóa: luôn dùng cặp `is_deleted` (bool, index) + `deleted_at` | Không để mỗi module tự chọn kiểu khác nhau | `PROJECT_CONSTITUTION.md` §9 |
| A13 | Tiền tệ luôn `DecimalField`, không dùng `Float` | Tránh sai số làm tròn với tiền | `PROJECT_CONSTITUTION.md` §9 |
| A14 | Lưu UTC trong DB (`USE_TZ=True`), convert giờ VN (UTC+7) ở tầng hiển thị | Chuẩn hóa timezone, tránh lệch giờ khi mở rộng | `PROJECT_CONSTITUTION.md` §9 |
| A15 | JWT (access ngắn hạn + refresh, rotation & blacklist khi logout); không hard-code role | Bảo mật xác thực chuẩn, role lấy từ claim/DB | `PROJECT_CONSTITUTION.md` §13, `CODING_STANDARDS.md` §8 |
| A16 | Webhook/callback thanh toán phải idempotent, lưu toàn bộ payload trước khi xử lý | Tránh cộng/trừ tiền trùng khi cổng thanh toán gọi lại | `PROJECT_CONSTITUTION.md` §15 |
| A17 | Consumer WebSocket không chứa business logic; mọi message ghi DB song song khi broadcast | WebSocket không phải nguồn dữ liệu duy nhất, hỗ trợ reconnect | `PROJECT_CONSTITUTION.md` §6 |
| A18 | PostgreSQL chạy ngoài docker-compose, qua biến môi trường; Dockerfile FE/BE multi-stage | Theo đúng đặc tả bàn giao | `PROJECT_CONSTITUTION.md` §17 |
| A19 | Test coverage tối thiểu 60% cho module core (giỏ hàng, checkout, voucher, tồn kho) + bắt buộc test concurrent chống oversell | Chốt cứng theo NFR-14, không chỉ là mục tiêu điểm số | `PROJECT_CONSTITUTION.md` §20 |
| A20 | Feature flag cho tính năng AI qua `SiteSetting`, không cần deploy lại | Giảm rủi ro khi AI lỗi/tốn chi phí bất thường | `PROJECT_CONSTITUTION.md` §24 |

---

## Phần B — Quyết định "chọn 1" còn tồn đọng

Nguồn: `TECH_STACK.md` mục 7. **Phải chốt trước khi code phần liên quan**, và khi chốt phải ghi lý do theo đúng AI Coding Rules (so sánh ưu/nhược trước khi chọn) — thêm entry vào Phần C khi chốt xong.

| # | Quyết định cần chốt | Các lựa chọn | Trạng thái |
|---|---|---|---|
| B1 | CSS framework | Tailwind CSS (khuyến nghị) hoặc Bootstrap 5 | ✅ Đã chốt: Tailwind CSS |
| B2 | Bộ icon | Heroicons hoặc FontAwesome | ✅ Đã chốt: Heroicons |
| B3 | Thư viện biểu đồ (Dashboard Admin & Seller) | Chart.js hoặc ApexCharts | ✅ Đã chốt: Chart.js |
| B4 | LLM Provider chính (mặc định) | OpenAI / Claude / Gemini — kiến trúc `AIService` vẫn phải provider-agnostic dù chọn gì | ✅ Đã chốt: Google Gemini |
| B5 | Embedding model cụ thể | VD `text-embedding-3-small` hay model tiếng Việt riêng | ✅ Đã chốt: `gemini-embedding-2` (1536 chiều) |
| B6 | Cổng thanh toán sandbox (ngoài COD) | VNPay / MoMo / Stripe test | ✅ Đã chốt: VNPay Sandbox |

> Lưu ý: `api_design.md` §12 đã dùng ví dụ `vnpay` cho `payment_method` trong request checkout mẫu — đây chỉ là ví dụ minh họa, **không phải quyết định đã chốt** cho B6.

---

## Phần C — Nhật ký quyết định mới (điền dần trong quá trình phát triển)

Dùng template dưới đây mỗi khi nhóm chốt một quyết định "chọn 1" ở Phần B, hoặc phát sinh quyết định kiến trúc mới ngoài phạm vi tài liệu gốc.

```
### [Mã, VD: B4] <Tên quyết định> — YYYY-MM-DD

**Bối cảnh:** vì sao cần quyết định này.

**Phương án xem xét:**
- Phương án 1 — ưu điểm / nhược điểm
- Phương án 2 — ưu điểm / nhược điểm

**Quyết định:** phương án được chọn.

**Lý do chọn:** ngắn gọn, tập trung vào yếu tố quyết định.

**Tác động:** module/tài liệu nào cần cập nhật theo (VD: TECH_STACK.md, .env.example...).
```

### B1 CSS framework — 2026-07-21

**Bối cảnh:** cần một framework CSS thống nhất cho storefront và dashboard Vue 3.

**Phương án xem xét:**
- Tailwind CSS — linh hoạt, responsive tốt, tích hợp trực tiếp với Vite; đổi lại template có thể chứa nhiều utility class và nhóm phải tự xây các component dùng chung.
- Bootstrap 5 — có nhiều component dựng sẵn và tạo prototype nhanh; đổi lại giao diện dễ mang phong cách Bootstrap, tùy biến sâu cần thêm Sass/JavaScript.

**Quyết định:** Tailwind CSS.

**Lý do chọn:** phù hợp kiến trúc component Vue, dễ tạo giao diện riêng cho đồ án và có tài liệu tích hợp Vite tốt.

**Tác động:** `frontend/package.json`, cấu hình Vite/CSS, component trong `frontend/src/shared/components/` và tài liệu hướng dẫn frontend.

### B2 Bộ icon — 2026-07-21

**Bối cảnh:** cần một bộ icon nhất quán, miễn phí và tương thích tốt với Vue 3.

**Phương án xem xét:**
- Heroicons — giấy phép MIT, có package Vue chính thức, import từng icon và đồng bộ thẩm mỹ với Tailwind; đổi lại số lượng icon/brand icon ít hơn.
- FontAwesome — danh mục icon và brand icon lớn; đổi lại có phân tách Free/Pro, cần nhiều package hơn và dễ tăng bundle nếu import cả bộ.

**Quyết định:** Heroicons.

**Lý do chọn:** miễn phí, gọn, đủ cho storefront/dashboard và kết hợp tự nhiên với Tailwind CSS.

**Tác động:** `frontend/package.json` và các component giao diện dùng `@heroicons/vue`.

### B3 Thư viện biểu đồ — 2026-07-21

**Bối cảnh:** dashboard Admin và Seller cần biểu đồ doanh thu, xu hướng và cơ cấu dữ liệu.

**Phương án xem xét:**
- Chart.js — giấy phép MIT rõ ràng, phổ biến và đủ các biểu đồ cơ bản; đổi lại một số tương tác phức tạp cần cấu hình thủ công.
- ApexCharts — giao diện và interaction dashboard tốt sẵn; đổi lại mô hình giấy phép kép làm tăng ràng buộc nếu phạm vi sử dụng thay đổi.

**Quyết định:** Chart.js.

**Lý do chọn:** đáp ứng đầy đủ dashboard của đồ án, tài liệu tốt và giảm rủi ro giấy phép.

**Tác động:** `frontend/package.json`, feature `admin-dashboard`, `seller-dashboard` và các chart component dùng chung.

### B4 LLM Provider chính — 2026-07-21

**Bối cảnh:** cần provider mặc định cho các tính năng AI nhưng vẫn phải giữ `AIService` provider-agnostic theo A10/AI-15.

**Phương án xem xét:**
- OpenAI — SDK/tài liệu tốt và hệ sinh thái rộng; đổi lại API tính phí riêng theo usage.
- Anthropic Claude — mạnh về diễn giải và nội dung dài; đổi lại API chủ yếu trả phí và cần provider khác cho embedding.
- Google Gemini — có free tier cho dự án nhỏ, tạo key thuận tiện và có cả generation/embedding; đổi lại free tier có quota/chính sách dữ liệu riêng và model ID có thể thay đổi theo thời gian.

**Quyết định:** Google Gemini là provider mặc định; model cụ thể cấu hình qua biến môi trường, không hard-code.

**Lý do chọn:** chi phí khởi đầu thấp, dễ setup cho đồ án và dùng chung hệ sinh thái với embedding; kiến trúc vẫn cho phép bổ sung provider khác mà không đổi code gọi.

**Tác động:** `AIService`, `GeminiProvider`, `AI_PROVIDER`/`AI_MODEL`/`GEMINI_API_KEY` trong `.env.example`, log token/chi phí và tài liệu AI.

### B5 Embedding model — 2026-07-21

**Bối cảnh:** semantic search/recommendation cần model hỗ trợ tốt dữ liệu tiếng Việt và tương thích schema pgvector.

**Phương án xem xét:**
- `gemini-embedding-2` — hỗ trợ đa ngôn ngữ, có free tier, cùng API key với provider chính và cho phép chọn kích thước vector; đổi lại phải pin kích thước và re-index toàn bộ khi đổi model/cấu hình.
- `text-embedding-3-small` — phổ biến, chi phí thấp và mặc định khớp vector 1536 chiều; đổi lại cần thêm OpenAI key/provider riêng.
- Model multilingual tự host như BGE-M3 — không tốn phí API và kiểm soát dữ liệu tốt; đổi lại tăng đáng kể RAM, image size và độ phức tạp vận hành.

**Quyết định:** `gemini-embedding-2` với `output_dimensionality=1536`.

**Lý do chọn:** hỗ trợ tiếng Việt, dùng chung provider/key với B4 và giữ nguyên thiết kế `ProductEmbedding.embedding = VECTOR(1536)`.

**Tác động:** `ProductEmbedding`, cấu hình `AI_EMBEDDING_MODEL`/`AI_EMBEDDING_DIMENSIONS`, Celery task re-index và tài liệu database/AI.

### B6 Cổng thanh toán sandbox — 2026-07-21

**Bối cảnh:** ngoài COD, đồ án cần một luồng thanh toán online có redirect, callback/IPN và kiểm thử idempotency.

**Phương án xem xét:**
- VNPay Sandbox — phù hợp VND/thẻ và ngân hàng Việt Nam, có sandbox và code mẫu Python; đổi lại tài liệu chủ yếu tiếng Việt và callback cần URL public khi test.
- MoMo — quen thuộc với người dùng Việt Nam; đổi lại onboarding và luồng app/QR phức tạp hơn cho demo web.
- Stripe test — tài liệu tiếng Anh và công cụ webhook tốt; đổi lại chưa phù hợp cho kịch bản triển khai thực tế của doanh nghiệp tại Việt Nam.

**Quyết định:** COD + VNPay Sandbox, trong đó VNPay là cổng thanh toán online mặc định.

**Lý do chọn:** sát bối cảnh thương mại điện tử Việt Nam, dùng VND, khớp hợp đồng API hiện có và thể hiện được đầy đủ luồng callback/idempotency.

**Tác động:** app `payment`, `VNPayProvider`, `PaymentTransaction`, biến môi trường `VNPAY_*`, callback public, test chữ ký/idempotency và tài liệu checkout/payment.

### C1 Frontend build/test toolchain security update — 2026-07-21

**Bối cảnh:** phiên bản Node 20 trong đặc tả ban đầu đã EOL; dependency audit của scaffold cũng xác định Vite 5 và Vitest 2 nằm trong dải phiên bản có security advisory, gồm advisory mức high/critical.

**Phương án xem xét:**
- Giữ Node 20 + Vite 5 + Vitest 2 — khớp phiên bản tài liệu cũ nhưng chấp nhận runtime EOL và các advisory đã biết.
- Nâng Node 22 LTS + Vite 8 + Vitest 4 — cần cập nhật toolchain/CI nhưng vẫn giữ nguyên Vue 3, TypeScript và kiến trúc frontend.

**Quyết định:** dùng Node 22 LTS (>=22.12), Vite 8 và Vitest 4.

**Lý do chọn:** đáp ứng NFR-03, tránh khởi tạo dự án mới trên runtime EOL hoặc dependency có lỗ hổng đã công bố.

**Tác động:** `TECH_STACK.md`, `project_context.md`, `frontend/package.json`, Dockerfile frontend, CI và README.

---

## Tài liệu liên quan

- `TECH_STACK.md` §7 — nguồn danh sách quyết định "chọn 1".
- `PROJECT_CONSTITUTION.md` — nguồn thẩm quyền của toàn bộ Phần A.
- `system_prompt.md` §6 — khi nào AI nên hỏi lại người dùng thay vì tự quyết định.
