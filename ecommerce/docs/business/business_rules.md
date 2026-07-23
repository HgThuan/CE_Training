# Business Rules

Tài liệu tập hợp các quy tắc nghiệp vụ cụ thể (business rules) rút ra từ đặc tả yêu cầu. Đây là các ràng buộc mà code **phải** thực thi đúng, khác với `CODING_STANDARDS.md` (quy chuẩn viết code) — tài liệu này nói về **luật chơi của nghiệp vụ**, không phải cách viết code.

Mỗi rule có mã `BR-<MODULE>-<SỐ>` để tiện tham chiếu từ code/test.

---

## 1. Tài khoản & Phân quyền

- **BR-ACC-01:** Một email chỉ gắn với đúng một tài khoản.
- **BR-ACC-02:** Tài khoản phải xác thực email trước khi đăng nhập lần đầu (trừ khi đăng nhập qua Google — CUS-03, coi như đã xác thực).
- **BR-ACC-03:** Đăng nhập sai mật khẩu quá số lần cho phép trong một khoảng thời gian → tạm khóa đăng nhập (rate limit), không khóa vĩnh viễn.
- **BR-ACC-04:** Tài khoản bị Admin khóa (`is_active = False`) không thể đăng nhập; token hiện có bị vô hiệu ngay, không cần đợi hết hạn.
- **BR-ACC-05:** Mỗi user có tối đa 1 địa chỉ giao hàng mặc định tại một thời điểm (ràng buộc unique có điều kiện).
- **BR-ACC-06:** Google Login: nếu email từ Google trùng với tài khoản email/password đã có, tự động liên kết vào tài khoản đó, không tạo tài khoản trùng.

## 2. Seller & Shop

- **BR-SHOP-01:** Một Customer chỉ có thể có tối đa 1 hồ sơ Seller đang hoạt động (không tạo nhiều shop từ cùng một tài khoản, trừ khi có yêu cầu khác từ nghiệp vụ mở rộng).
- **BR-SHOP-02:** Sản phẩm chỉ được tạo mới sau khi hồ sơ Seller ở trạng thái `approved`.
- **BR-SHOP-03:** Khi Shop bị khóa (`shop_status = locked`): toàn bộ sản phẩm của shop tự động ẩn khỏi trang mua sắm; Seller không tạo được đơn/sản phẩm mới nhưng **vẫn phải xử lý được** các đơn cũ đang dở dang (không được để đơn hàng "mồ côi").
- **BR-SHOP-04:** Mọi truy vấn dữ liệu của Seller (sản phẩm, đơn hàng, kho, voucher, khách hàng) phải scope theo `shop_id` thuộc chính Seller đang đăng nhập — không tin bất kỳ `shop_id` nào gửi từ client.

## 3. Sản phẩm & Biến thể

- **BR-PRD-01:** Sản phẩm mới tạo hoặc có "sửa lớn" (thay đổi giá, danh mục, thông tin chính) phải qua Admin duyệt trước khi hiển thị công khai; chỉ sản phẩm trạng thái `approved` xuất hiện ở API public.
- **BR-PRD-02:** SKU là duy nhất trong phạm vi một shop (không cần duy nhất toàn sàn).
- **BR-PRD-03:** Mỗi sản phẩm tối đa 9 ảnh + 1 video.
- **BR-PRD-04:** Sản phẩm bị Admin ẩn/xóa vì vi phạm phải kèm lý do gửi cho Seller, và được ghi vào Audit Log.
- **BR-PRD-05:** Danh mục là cấu trúc cây tối thiểu 2 cấp; sản phẩm phải gắn với danh mục lá (cấp thấp nhất), không gắn với danh mục cha có danh mục con.

## 4. Kho (Inventory)

- **BR-INV-01:** Tồn kho không bao giờ được phép âm — ràng buộc ở cả tầng ứng dụng (`select_for_update` trước khi trừ) và tầng DB (`CheckConstraint`).
- **BR-INV-02:** Phiếu nhập/xuất kho đã xác nhận thì không được sửa; sai sót phải tạo phiếu điều chỉnh mới, không sửa ngược lịch sử.
- **BR-INV-03:** Mọi biến động tồn kho (nhập, xuất, bán, hoàn, điều chỉnh) đều phải ghi vào `StockMovement` — không có đường tắt nào thay đổi tồn kho mà không để lại vết.
- **BR-INV-04:** Khi đơn hàng bị hủy hoặc hoàn, tồn kho phải được hoàn lại đúng số lượng đã trừ, trong cùng transaction với việc đổi trạng thái đơn.
- **BR-INV-05:** Ngưỡng cảnh báo sắp hết hàng (`low_stock_threshold`) do từng Seller tự cấu hình theo sản phẩm; nếu không cấu hình, dùng ngưỡng mặc định toàn hệ thống (từ System Config).

## 5. Giỏ hàng & Checkout

- **BR-CART-01:** Giỏ hàng của khách vãng lai lưu ở client (localStorage); khi đăng nhập, merge vào giỏ DB — nếu cùng sản phẩm/biến thể đã có trong giỏ DB, cộng dồn số lượng (không tạo dòng trùng).
- **BR-CART-02:** Một đơn hàng (`Order`) chỉ chứa sản phẩm của **một** shop. Giỏ hàng có sản phẩm từ nhiều shop → checkout tạo ra nhiều `Order` tương ứng, mỗi order tính phí ship và áp voucher độc lập.
- **BR-CART-03:** Tại thời điểm checkout, hệ thống phải kiểm tra lại tồn kho và giá hiện tại — không tin dữ liệu giá/tồn kho đã cache từ lúc thêm vào giỏ. Nếu giá thay đổi, cảnh báo Customer trước khi xác nhận đặt hàng.
- **BR-CART-04:** Không tạo đơn hàng "một phần" — nếu một item trong giỏ hết hàng ngay lúc checkout, toàn bộ order của shop đó không được tạo cho tới khi Customer cập nhật lại giỏ.

## 6. Voucher & Khuyến mãi

- **BR-PROMO-01:** Voucher có phạm vi `platform` (sàn) hoặc `shop` (riêng từng shop). Một đơn có thể áp dụng đồng thời 1 voucher sàn + 1 voucher shop (không áp 2 voucher cùng phạm vi trong 1 đơn, trừ khi nghiệp vụ mở rộng cho phép).
- **BR-PROMO-02:** Voucher giới hạn 1 lượt/người phải có ràng buộc unique (coupon, user) ở tầng DB, không chỉ check ở tầng ứng dụng.
- **BR-PROMO-03:** Voucher chỉ được ghi nhận sử dụng (`CouponUsage`) khi đơn hàng được tạo thành công; nếu đơn bị hủy trước khi xác nhận, lượt dùng voucher phải được hoàn lại.
- **BR-PROMO-04:** Flash Sale: số lượng bán ở giá sale bị giới hạn riêng theo từng sản phẩm, tách biệt với tồn kho thông thường; hết số lượng sale → sản phẩm tự động trả về giá gốc dù chưa hết khung giờ.
- **BR-PROMO-05:** Ngoài khung giờ Flash Sale, giá sản phẩm tự động trở về giá gốc (xử lý bằng Celery beat, không phụ thuộc vào việc có request nào gọi tới hay không).

## 7. Đơn hàng (Order)

- **BR-ORD-01:** Đơn hàng chỉ được Customer **hủy trực tiếp** khi ở trạng thái "Chờ xác nhận". Từ "Đã xác nhận" trở đi, Customer chỉ có thể yêu cầu trả hàng/hoàn tiền sau khi nhận hàng.
- **BR-ORD-02:** Mỗi lần chuyển trạng thái đơn hàng phải ghi vào `OrderStatusHistory` kèm thời điểm và người/thao tác thực hiện — không cho phép chuyển trạng thái mà không để lại lịch sử.
- **BR-ORD-03:** Chuyển trạng thái đơn hàng phải tuân theo state machine hợp lệ (xem `workflows.md`) — không cho phép nhảy cóc trạng thái (vd: từ "Chờ xác nhận" thẳng sang "Đang giao").
- **BR-ORD-04:** Khi đơn bị hủy: hoàn tồn kho + hoàn lượt sử dụng voucher, thực hiện trong cùng một transaction.
- **BR-ORD-05:** Yêu cầu trả hàng/hoàn tiền chỉ được mở trong X ngày kể từ khi đơn chuyển sang "Hoàn thành" (X là tham số cấu hình được ở System Config).
- **BR-ORD-06:** Nếu Seller từ chối yêu cầu trả hàng và Customer không đồng ý, yêu cầu tự động leo thang thành `Dispute` để Admin xử lý — không được để yêu cầu "treo" không có lối ra.

## 8. Thanh toán

- **BR-PAY-01:** Mọi callback/IPN từ cổng thanh toán phải được xử lý idempotent — cùng một mã giao dịch không được xử lý (cộng/trừ tiền, đổi trạng thái đơn) quá 1 lần.
- **BR-PAY-02:** Trạng thái thanh toán thực tế lấy từ cổng thanh toán (qua callback) là nguồn sự thật (source of truth) — không suy đoán trạng thái thanh toán chỉ dựa trên hành động của Customer ở FE.
- **BR-PAY-03:** Đơn COD không tạo `PaymentTransaction` chờ callback — coi như "thanh toán khi nhận hàng", trạng thái thanh toán được xác nhận thủ công khi Seller/shipper xác nhận đã thu tiền.

## 9. Đánh giá (Review)

- **BR-REV-01:** Chỉ Customer đã mua và đơn hàng chứa sản phẩm đó đã ở trạng thái "Hoàn thành" mới được viết đánh giá (verified purchase).
- **BR-REV-02:** Mỗi `(order_item, user)` chỉ được đánh giá đúng 1 lần; được sửa trong vòng 7 ngày kể từ khi đánh giá, sau đó khóa.
- **BR-REV-03:** Seller chỉ được phản hồi 1 lần cho mỗi review (được sửa phản hồi, không tạo nhiều phản hồi).
- **BR-REV-04:** Điểm trung bình sản phẩm phải được cập nhật ngay khi có review mới/review bị ẩn (qua signal), không để lệch với dữ liệu review thực tế.

## 10. Chat & Thông báo

- **BR-CHAT-01:** Chỉ hai bên liên quan trực tiếp (Seller của shop và Customer đang chat) được truy cập vào một cuộc hội thoại — không có "phòng chat công khai".
- **BR-CHAT-02:** Tin nhắn phải được lưu DB trước khi coi là gửi thành công; broadcast qua WebSocket là thao tác thêm (best-effort), không phải điều kiện để tin nhắn được xem là đã gửi.

## 11. AI Features

- **BR-AI-01:** Mọi nội dung do AI sinh ra và hiển thị cho người dùng cuối phải có nhãn "Tạo bởi AI".
- **BR-AI-02:** AI không được tự ý publish nội dung thay Seller — mô tả/tiêu đề do AI sinh ra chỉ là gợi ý, Seller phải xem và lưu thì mới áp dụng.
- **BR-AI-03:** Chatbot AI chỉ được gợi ý sản phẩm **thật sự tồn tại trên sàn** — không được "bịa" sản phẩm hoặc thông tin giá/tồn kho không khớp dữ liệu thực tế.
- **BR-AI-04:** Với AI Sales Analytics, số liệu định lượng (doanh thu, tăng/giảm %) phải được tính bằng SQL trước; LLM chỉ được dùng để diễn giải, không được tự tính toán con số cuối cùng hiển thị cho người dùng.
- **BR-AI-05:** Khi AI provider lỗi hoặc timeout, tính năng liên quan phải suy giảm nhẹ nhàng (graceful degradation) — không được chặn luồng nghiệp vụ chính (ví dụ: xem sản phẩm, checkout vẫn hoạt động dù AI đang lỗi).

## 12. Bảo mật & Vận hành

- **BR-SEC-01:** Không có endpoint nào tin tưởng `user_id`/`shop_id` gửi từ client để xác định quyền sở hữu dữ liệu — luôn lấy từ thông tin xác thực (`request.user`).
- **BR-SEC-02:** Hành động nhạy cảm (khóa tài khoản, duyệt seller, sửa/xóa sản phẩm người khác, đổi quyền) bắt buộc ghi Audit Log, không có ngoại lệ "vì gấp".
- **BR-SEC-03:** File upload phải được validate loại và dung lượng thực tế (kiểm tra content-type thật của file, không chỉ dựa vào đuôi file).

## Tài liệu liên quan

- `roles.md`, `modules.md` — bối cảnh vai trò/module áp dụng các rule trên.
- `use_cases.md` — nơi các rule này được áp dụng trong luồng cụ thể.
- `workflows.md` — state machine chi tiết cho các rule liên quan tới chuyển trạng thái (Order, Return/Dispute, Seller Onboarding, Product).
- `PROJECT_CONSTITUTION.md` (mục 8, 14, 15) — cách các rule về concurrency, multi-tenant, idempotency được đảm bảo ở tầng kỹ thuật.
