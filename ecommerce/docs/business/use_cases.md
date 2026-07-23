# Use Cases

Tài liệu mô tả các kịch bản sử dụng (use case) chính của hệ thống, theo định dạng: **Actor — Tiền điều kiện — Luồng chính — Luồng thay thế/ngoại lệ**. Chỉ liệt kê các use case quan trọng/phức tạp; các use case CRUD đơn giản (ví dụ CRUD thương hiệu) không lặp lại chi tiết vì đã rõ trong đặc tả.

Ký hiệu mã use case: `UC-<MODULE>-<SỐ>`.

---

## A. Account & Auth

### UC-ACC-01: Khách hàng đăng ký tài khoản
- **Actor:** Khách hàng (chưa có tài khoản)
- **Tiền điều kiện:** Email chưa tồn tại trong hệ thống
- **Luồng chính:**
  1. Người dùng nhập email, mật khẩu, xác nhận mật khẩu
  2. Hệ thống validate định dạng email, độ mạnh mật khẩu
  3. Hệ thống tạo tài khoản ở trạng thái chưa xác thực, gửi email kích hoạt (Celery task)
  4. Người dùng bấm link kích hoạt trong email
  5. Tài khoản chuyển trạng thái đã xác thực, có thể đăng nhập
- **Luồng thay thế:**
  - 2a. Email đã tồn tại → báo lỗi, gợi ý đăng nhập hoặc quên mật khẩu
  - 4a. Link hết hạn → cho phép gửi lại email kích hoạt

### UC-ACC-02: Đăng nhập & tự động refresh token
- **Actor:** Người dùng đã có tài khoản (cả 3 vai trò)
- **Luồng chính:**
  1. Người dùng nhập email + mật khẩu
  2. Hệ thống xác thực, trả JWT access + refresh token
  3. FE lưu access token trong memory, gọi API kèm token
  4. Khi access token hết hạn, axios interceptor tự động gọi refresh, lấy access token mới, retry request gốc
- **Luồng thay thế:**
  - 2a. Sai mật khẩu quá N lần → tạm khóa đăng nhập theo rate limit
  - 4a. Refresh token cũng hết hạn/bị blacklist → chuyển về trang đăng nhập

### UC-ACC-03: Admin khóa tài khoản vi phạm
- **Actor:** Admin
- **Luồng chính:**
  1. Admin tìm tài khoản cần khóa, nhập lý do
  2. Hệ thống set `is_active = False`, ghi Audit Log
  3. Gửi email thông báo cho người bị khóa (Celery task)
  4. Mọi token hiện có của user bị vô hiệu (middleware chặn)
- **Kết quả:** người dùng không đăng nhập được (Customer) hoặc không bán được (Seller) cho tới khi được mở khóa.

---

## B. Seller Onboarding

### UC-SEL-01: Customer đăng ký trở thành Seller
- **Actor:** Customer đã đăng nhập
- **Tiền điều kiện:** Chưa có `SellerProfile` hoặc hồ sơ trước đã bị từ chối
- **Luồng chính:**
  1. Customer điền form nhiều bước: thông tin shop, thông tin liên hệ, upload giấy tờ (CCCD, giấy phép KD...)
  2. Hệ thống tạo hồ sơ trạng thái `pending`
  3. Admin xem hồ sơ trong hàng chờ duyệt (ADM-09)
  4. Admin duyệt → `approved`, tạo `SellerProfile` + `Shop`, gửi thông báo/email
  5. Customer giờ có thể truy cập khu vực quản trị Seller
- **Luồng thay thế:**
  - 4a. Admin từ chối kèm lý do → `rejected`, Customer nhận thông báo, có thể nộp lại hồ sơ
  - 4b. Thiếu giấy tờ xác minh → Admin yêu cầu bổ sung (ADM-10), hồ sơ giữ ở trạng thái chờ bổ sung

Xem sơ đồ trạng thái chi tiết ở `workflows.md` mục "Seller Onboarding".

---

## C. Product & Inventory

### UC-PRD-01: Seller tạo sản phẩm mới với biến thể
- **Actor:** Seller
- **Luồng chính:**
  1. Seller nhập thông tin cơ bản: tên, danh mục, thương hiệu, mô tả, giá gốc/giá bán
  2. Seller upload tối đa 9 ảnh + 1 video, sắp xếp thứ tự, chọn ảnh đại diện
  3. Seller định nghĩa thuộc tính biến thể (màu, size...); hệ thống sinh tổ hợp biến thể tự động
  4. Với mỗi biến thể: nhập SKU (hoặc tự sinh), giá riêng, tồn kho ban đầu, ảnh riêng (tùy chọn)
  5. Sản phẩm lưu ở trạng thái `draft`
  6. Seller gửi duyệt → trạng thái `pending`
  7. Admin duyệt (UC-ADM-03) → `approved`, sản phẩm hiển thị công khai
- **Luồng thay thế:**
  - 4a. SKU trùng trong shop → báo lỗi, yêu cầu nhập SKU khác
  - 7a. Admin từ chối kèm lý do → sản phẩm về trạng thái cần chỉnh sửa, Seller sửa và gửi duyệt lại

### UC-PRD-02: Seller nhập kho
- **Actor:** Seller
- **Luồng chính:**
  1. Seller tạo phiếu nhập: chọn sản phẩm/biến thể, số lượng, giá nhập, nhà cung cấp
  2. Seller xác nhận phiếu
  3. Hệ thống cộng tồn kho (trong `transaction.atomic()`), ghi `StockMovement`
- **Luồng thay thế:**
  - 2a. Phiếu đã xác nhận không được sửa — chỉ có thể tạo phiếu điều chỉnh mới nếu sai sót.

### UC-PRD-03: Hệ thống cảnh báo sắp hết hàng
- **Actor:** Hệ thống (tự động), Seller (thiết lập ngưỡng)
- **Luồng chính:**
  1. Seller đặt `low_stock_threshold` cho từng sản phẩm/biến thể
  2. Khi tồn kho giảm (do bán hoặc điều chỉnh) chạm ngưỡng, hệ thống bắn notification in-app cho Seller
  3. Seller xem danh sách sản phẩm sắp hết hàng trên dashboard

---

## D. Cart, Checkout & Payment

### UC-ORD-01: Khách hàng thêm sản phẩm vào giỏ (bao gồm khách vãng lai)
- **Actor:** Customer (đã đăng nhập hoặc khách vãng lai)
- **Luồng chính:**
  1. Khách chọn biến thể (màu/size), số lượng trên trang chi tiết sản phẩm
  2. Nếu đã đăng nhập: giỏ hàng lưu ở DB theo user
  3. Nếu khách vãng lai: giỏ hàng lưu ở `localStorage`
  4. Khi khách đăng nhập, giỏ localStorage được merge vào giỏ DB (xử lý trùng sản phẩm: cộng dồn số lượng)
- **Luồng thay thế:**
  - 1a. Biến thể hết hàng → không cho thêm vào giỏ, hiển thị nút "Báo tôi khi có hàng" (BON-09)

### UC-ORD-02: Checkout & đặt hàng (nhiều shop trong 1 giỏ)
- **Actor:** Customer
- **Tiền điều kiện:** Giỏ hàng có ít nhất 1 sản phẩm còn hàng
- **Luồng chính:**
  1. Customer chọn địa chỉ giao hàng
  2. Customer chọn/nhập voucher (sàn + shop), hệ thống hiển thị số tiền giảm cho từng shop
  3. Hệ thống tính phí ship từng shop theo bảng cấu hình
  4. Customer chọn phương thức thanh toán (COD / cổng sandbox)
  5. Customer xác nhận đặt hàng
  6. Hệ thống, trong `transaction.atomic()` cho từng shop:
     - Tạo 1 `Order` riêng cho mỗi shop trong giỏ
     - Trừ tồn kho từng item (`select_for_update`)
     - Ghi nhận sử dụng voucher (`CouponUsage`)
  7. Nếu thanh toán online: redirect sang cổng thanh toán; nếu COD: đơn vào thẳng trạng thái "Chờ xác nhận"
- **Luồng thay thế:**
  - 6a. Một item hết hàng giữa lúc checkout (khác giỏ lúc thêm) → báo lỗi, yêu cầu Customer cập nhật giỏ, không tạo đơn một phần
  - 6b. Voucher hết lượt dùng/hết hạn giữa lúc checkout → báo lỗi, bỏ voucher khỏi đơn, yêu cầu xác nhận lại tổng tiền

Xem chi tiết luồng ở `workflows.md` mục "Checkout".

### UC-ORD-03: Xử lý callback thanh toán (IPN)
- **Actor:** Hệ thống (nhận callback từ cổng thanh toán)
- **Luồng chính:**
  1. Cổng thanh toán gọi endpoint IPN với mã giao dịch + trạng thái
  2. Hệ thống kiểm tra mã giao dịch đã xử lý chưa (idempotency check)
  3. Nếu chưa xử lý: ghi `PaymentTransaction`, cập nhật trạng thái đơn hàng tương ứng, bắn notification cho Customer
  4. Nếu đã xử lý trước đó: trả về thành công ngay, không xử lý lại (tránh cộng/trừ tiền 2 lần)
- **Ngoại lệ:** chữ ký callback không hợp lệ → từ chối, ghi log cảnh báo bảo mật.

---

## E. Order Fulfillment (Seller & Admin)

### UC-ORD-04: Seller xử lý đơn hàng theo luồng trạng thái
- **Actor:** Seller
- **Luồng chính:** xem chi tiết ở `workflows.md` mục "Order Status Flow". Tóm tắt: Chờ xác nhận → Đã xác nhận → Đang đóng gói → Đang giao → Hoàn thành.
- Mỗi bước chuyển trạng thái: ghi `OrderStatusHistory`, bắn thông báo cho Customer.

### UC-ORD-05: Customer hủy đơn
- **Actor:** Customer
- **Tiền điều kiện:** Đơn đang ở trạng thái "Chờ xác nhận" (chưa được Seller xác nhận)
- **Luồng chính:**
  1. Customer chọn "Hủy đơn", nhập lý do
  2. Hệ thống chuyển trạng thái đơn sang "Đã hủy" trong transaction
  3. Hoàn tồn kho các item trong đơn
  4. Hoàn lượt sử dụng voucher (nếu có) để Customer dùng lại được
- **Ngoại lệ:** đơn đã ở trạng thái "Đã xác nhận" trở đi → không cho hủy trực tiếp, Customer chỉ có thể yêu cầu trả hàng/hoàn tiền sau khi nhận (UC-ORD-06).

### UC-ORD-06: Yêu cầu trả hàng/hoàn tiền → leo thang thành tranh chấp
- **Actor:** Customer, Seller, Admin
- **Luồng chính:**
  1. Trong X ngày sau khi nhận hàng, Customer mở yêu cầu hoàn/trả kèm ảnh & lý do
  2. Seller xem, đồng ý hoặc từ chối
  3. Nếu Seller đồng ý → xử lý hoàn tiền, đơn cập nhật trạng thái tương ứng
  4. Nếu Seller từ chối và Customer không đồng ý → leo thang thành `Dispute`, chuyển cho Admin
  5. Admin xem chứng cứ 2 bên, ra quyết định: hoàn tiền / từ chối / hoàn một phần
- Xem sơ đồ trạng thái ở `workflows.md` mục "Return & Dispute Flow".

---

## F. Promotion

### UC-PRM-01: Áp dụng Flash Sale
- **Actor:** Customer (mua), Seller/Admin (tạo)
- **Luồng chính:**
  1. Admin tạo Flash Sale: khung giờ, danh sách sản phẩm, giá sale, số lượng giới hạn từng sản phẩm
  2. Trong khung giờ diễn ra: trang chủ hiển thị đếm ngược, sản phẩm hiển thị giá sale
  3. Khi Customer đặt hàng sản phẩm Flash Sale: kiểm tra & trừ tồn kho sale riêng (dùng `F()` expression tránh race condition)
  4. Hết khung giờ: hệ thống tự động trả sản phẩm về giá gốc (Celery beat)
- **Ngoại lệ:** số lượng sale đã hết trước khi hết giờ → sản phẩm hiển thị "Đã kết thúc", không cho đặt thêm ở giá sale.

### UC-PRM-02: Áp dụng voucher sàn + voucher shop trong cùng đơn
- **Actor:** Customer
- **Luồng chính:**
  1. Customer nhập/chọn voucher sàn (áp dụng toàn đơn) và voucher shop (áp dụng riêng cho sản phẩm của shop đó)
  2. Hệ thống validate từng voucher: đơn tối thiểu, số lượt dùng còn lại, số lượt/người, thời hạn, phạm vi
  3. Hệ thống cộng dồn giảm giá theo đúng phạm vi của từng voucher, hiển thị số tiền giảm minh bạch theo từng shop

---

## G. Review

### UC-REV-01: Customer viết đánh giá sau khi nhận hàng
- **Actor:** Customer
- **Tiền điều kiện:** Đơn hàng chứa sản phẩm đã ở trạng thái "Hoàn thành"
- **Luồng chính:**
  1. Customer chọn 1-5 sao, viết bình luận, đính kèm tối đa 5 ảnh + 1 video
  2. Hệ thống lưu review, gắn ràng buộc unique (order_item, user) — mỗi sản phẩm/đơn chỉ đánh giá 1 lần
  3. Hệ thống cập nhật điểm trung bình sản phẩm (denormalize qua signal)
  4. Customer có thể sửa đánh giá trong 7 ngày
- **Luồng liên quan:** Seller trả lời công khai review (UC-REV-02); AI tự động tóm tắt review khi đủ N review mới (AI-07).

---

## H. AI Features

### UC-AI-01: Customer dùng AI Smart Search
- **Actor:** Customer
- **Luồng chính:**
  1. Customer nhập nhu cầu bằng ngôn ngữ tự nhiên (vd: "laptop học AI dưới 20 triệu")
  2. AIService gọi LLM trích xuất ràng buộc có cấu trúc (loại hàng, khoảng giá, thuộc tính) — function calling
  3. Hệ thống kết hợp semantic search (embeddings, pgvector) với filter SQL (giá, danh mục)
  4. Trả kết quả kèm giải thích ngắn vì sao gợi ý
- **Ngoại lệ:** AI provider lỗi/timeout → fallback về tìm kiếm từ khóa thông thường (UC không được để trắng kết quả).

### UC-AI-02: Customer trò chuyện với AI Shopping Assistant
- **Actor:** Customer
- **Luồng chính:**
  1. Customer mở chatbot, đặt câu hỏi hoặc mô tả nhu cầu
  2. AIService giữ ngữ cảnh hội thoại theo session, dùng tool use (`search_products`, `get_product`, `get_policy`)
  3. Chatbot hỏi lại làm rõ nhu cầu nếu chưa đủ thông tin
  4. Chatbot trả về sản phẩm thật của sàn kèm card sản phẩm bấm được, có thể so sánh, hoặc trả lời chính sách giao/đổi trả
  5. Câu trả lời stream qua SSE/WebSocket
- **Ngoại lệ:** câu hỏi ngoài phạm vi (AI-06) → chuyển tiếp cho Seller/CSKH kèm tóm tắt hội thoại.

### UC-AI-03: Seller dùng AI sinh mô tả sản phẩm
- **Actor:** Seller
- **Luồng chính:**
  1. Seller nhập tên sản phẩm + vài từ khóa trong form tạo sản phẩm
  2. AIService sinh tiêu đề chuẩn SEO, mô tả bán hàng, meta description (trả về JSON có cấu trúc)
  3. Seller xem, chỉnh sửa nếu cần, bấm "Tạo lại" (regenerate) nếu chưa ưng ý
  4. Seller lưu — nội dung cuối cùng do Seller quyết định, AI chỉ hỗ trợ soạn thảo

---

## I. Chat & Notification

### UC-CHAT-01: Customer chat với Shop
- **Actor:** Customer, Seller
- **Luồng chính:**
  1. Customer mở khung chat từ trang sản phẩm/shop
  2. Kết nối WebSocket (xác thực bằng JWT ở handshake), join group `conversation_{id}`
  3. Gửi tin nhắn text/ảnh, lưu vào DB, broadcast tới Seller đang online
  4. Nếu Seller offline: tin nhắn vẫn lưu, đếm số tin chưa đọc, Seller thấy khi đăng nhập lại

---

## Tài liệu liên quan

- `roles.md` — vai trò thực hiện từng use case.
- `modules.md` — module chứa từng use case.
- `business_rules.md` — các ràng buộc nghiệp vụ chi tiết áp dụng trong luồng chính/thay thế ở trên.
- `workflows.md` — sơ đồ trạng thái đầy đủ cho các luồng nhiều bước (Order, Seller Onboarding, Product, Return/Dispute, Flash Sale).
