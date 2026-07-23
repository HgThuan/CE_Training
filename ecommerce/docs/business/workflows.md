# Workflows

Tài liệu mô tả các luồng trạng thái (state machine) và quy trình nhiều bước quan trọng nhất của hệ thống. Đây là phần dễ sai nhất khi hiện thực — mọi thay đổi trạng thái phải đi qua đúng luồng mô tả ở đây, không được nhảy cóc (xem `business_rules.md` mục BR-ORD-03).

---

## 1. Order Status Flow (Luồng trạng thái đơn hàng)

Áp dụng cho module Order (SEL-10, CUS-16..17).

```
                 ┌──────────────┐
                 │ Chờ xác nhận │  ← trạng thái khởi tạo sau checkout
                 └──────┬───────┘
                        │ Seller xác nhận         │ Customer hủy (BR-ORD-01)
                        ▼                          ▼
                 ┌──────────────┐            ┌───────────┐
                 │  Đã xác nhận  │            │  Đã hủy   │ (hoàn tồn kho + hoàn voucher)
                 └──────┬───────┘            └───────────┘
                        │ Seller đóng gói
                        ▼
                 ┌────────────────┐
                 │ Đang đóng gói   │
                 └──────┬─────────┘
                        │ Seller bàn giao vận chuyển
                        ▼
                 ┌──────────────┐
                 │  Đang giao    │
                 └──────┬───────┘
                        │ Giao thành công
                        ▼
                 ┌──────────────┐
                 │  Hoàn thành   │──► (mở cửa sổ X ngày cho Return/Refund — xem mục 3)
                 └──────────────┘
```

**Quy tắc chuyển trạng thái:**

| Từ | Đến | Ai thực hiện | Điều kiện / hệ quả |
|---|---|---|---|
| Chờ xác nhận | Đã xác nhận | Seller | — |
| Chờ xác nhận | Đã hủy | Customer hoặc Seller | Hoàn tồn kho, hoàn lượt voucher |
| Đã xác nhận | Đang đóng gói | Seller | — |
| Đang đóng gói | Đang giao | Seller | In phiếu giao hàng (SEL-11) |
| Đang giao | Hoàn thành | Seller / hệ thống vận chuyển | Mở cửa sổ cho phép đánh giá (Review) và yêu cầu trả hàng |
| (bất kỳ trạng thái nào từ "Đã xác nhận" trở đi) | — | Customer | **Không được hủy trực tiếp** — chỉ có thể yêu cầu trả hàng sau khi "Hoàn thành" |

**Mỗi lần chuyển trạng thái** ghi vào `OrderStatusHistory` (trạng thái cũ, trạng thái mới, thời điểm, người thực hiện, ghi chú) và bắn notification cho Customer (BR-ORD-02).

---

## 2. Checkout Flow (Luồng đặt hàng)

Áp dụng cho CUS-13..15.

```
Giỏ hàng (nhiều shop)
      │
      ▼
Chọn địa chỉ giao hàng
      │
      ▼
Nhập/chọn voucher (sàn + shop) ──► validate từng voucher (BR-PROMO-01..03)
      │
      ▼
Tính phí ship theo từng shop (bảng cấu hình)
      │
      ▼
Chọn phương thức thanh toán (COD / cổng sandbox)
      │
      ▼
Xác nhận đặt hàng
      │
      ▼
┌─────────────────────────────────────────────┐
│  Với MỖI shop trong giỏ (transaction riêng): │
│    1. Kiểm tra lại tồn kho + giá hiện tại     │
│    2. select_for_update() trừ tồn kho từng item│
│    3. Tạo Order (trạng thái "Chờ xác nhận")    │
│    4. Ghi CouponUsage cho voucher đã áp dụng    │
└─────────────────────────────────────────────┘
      │
      ├── Thanh toán COD ──► Order giữ "Chờ xác nhận", chờ Seller xử lý
      │
      └── Thanh toán online ──► Redirect sang cổng thanh toán
                                       │
                                       ▼
                              Chờ callback/IPN (xem mục 5)
```

**Điểm cần lưu ý:** nếu bất kỳ shop nào trong giỏ có item hết hàng ở bước kiểm tra lại, **toàn bộ order của shop đó** không được tạo — không tạo đơn thiếu sót (BR-CART-04). Các shop khác trong cùng giỏ vẫn xử lý bình thường (mỗi shop là 1 transaction độc lập).

---

## 3. Return & Dispute Flow (Trả hàng / Hoàn tiền / Tranh chấp)

Áp dụng cho CUS-18, ADM-18.

```
Order = "Hoàn thành"
      │  (trong vòng X ngày — cấu hình được)
      ▼
Customer mở ReturnRequest (kèm ảnh + lý do)
      │
      ▼
   ┌────────────┐
   │   Open      │
   └──────┬─────┘
          │ Seller xem xét
          ▼
   ┌──────────────┐        ┌──────────────┐
   │  Đồng ý        │        │  Từ chối       │
   └──────┬───────┘        └──────┬───────┘
          │                        │
          ▼                        ▼
   Xử lý hoàn tiền           Customer đồng ý?
   (qua Wallet/Payment)          │
   → Resolved                ┌───┴────┐
                              │        │
                             Có        Không
                              │        │
                              ▼        ▼
                          Resolved   Leo thang → Dispute (Admin)
```

**Dispute (Admin xử lý):**
```
Dispute = "open"
      │ Admin xem chứng cứ 2 bên (ảnh, mô tả từ Customer & Seller)
      ▼
Dispute = "reviewing"
      │ Admin trao đổi thêm nếu cần
      ▼
Admin ra quyết định
      │
      ├── Hoàn tiền toàn bộ ──► Resolved (refund_full)
      ├── Từ chối ─────────────► Resolved (rejected)
      └── Hoàn một phần ───────► Resolved (refund_partial)
```

Quyết định của Admin là **cuối cùng** — không có bước leo thang cao hơn trong phạm vi hệ thống này.

---

## 4. Seller Onboarding Flow (Đăng ký & duyệt Seller)

Áp dụng cho SEL-18, ADM-09..10.

```
Customer nộp hồ sơ đăng ký bán hàng
      │
      ▼
   pending ──────────────────────────┐
      │                               │
      │ Admin yêu cầu bổ sung giấy tờ │
      │◄──────────────────────────────┘
      │
      │ Admin duyệt              │ Admin từ chối (kèm lý do)
      ▼                          ▼
   approved                   rejected
      │                          │
      ▼                          ▼
Tạo SellerProfile + Shop    Customer có thể nộp lại hồ sơ mới
(có thể tạo sản phẩm)       (quay lại "pending")
```

Sau khi `approved`, Shop ở trạng thái hoạt động bình thường cho tới khi Admin chủ động khóa (xem mục 6).

---

## 5. Payment Callback Flow (Xử lý IPN/Callback thanh toán)

Áp dụng cho CUS-15.

```
Cổng thanh toán gọi endpoint IPN
      │
      ▼
Xác thực chữ ký callback hợp lệ?
      │
   Không ──► Từ chối (401/400), ghi log cảnh báo
      │
     Có
      ▼
Mã giao dịch đã được xử lý trước đó? (idempotency check)
      │
     Có ──► Trả về thành công ngay, KHÔNG xử lý lại (BR-PAY-01)
      │
   Chưa
      ▼
Ghi PaymentTransaction (toàn bộ payload)
      │
      ▼
Cập nhật trạng thái thanh toán của Order tương ứng
      │
      ▼
Bắn notification cho Customer
```

---

## 6. Shop Lock Flow (Khóa gian hàng vi phạm)

Áp dụng cho ADM-11.

```
Admin phát hiện vi phạm → khóa Shop (shop_status = locked), kèm lý do
      │
      ▼
Ngay lập tức:
   - Toàn bộ sản phẩm của shop ẩn khỏi trang mua sắm (queryset public luôn filter theo shop_status)
   - Seller không tạo được sản phẩm/đơn mới
      │
      ▼
Đơn hàng ĐANG XỬ LÝ (chưa Hoàn thành/Đã hủy) của shop VẪN phải xử lý được
   (Seller vẫn đăng nhập được để hoàn tất đơn cũ — không được "khóa cứng" toàn bộ tài khoản)
      │
      ▼
Admin mở khóa (nếu vi phạm đã được giải quyết) → shop_status = active
```

---

## 7. Product Approval Flow (Duyệt sản phẩm)

Áp dụng cho ADM-13, SEL-02.

```
Seller tạo/sửa lớn sản phẩm
      │
      ▼
   draft ──► Seller gửi duyệt ──► pending
      │                              │
      │                    Admin duyệt│Admin từ chối (kèm lý do)
      │                              ▼                    ▼
      │                          approved              cần chỉnh sửa
      │                       (hiển thị public)      (Seller sửa, gửi lại)
      ▼
Sản phẩm chỉ ở trạng thái draft/pending KHÔNG xuất hiện ở API public (BR-PRD-01)
```

**Lưu ý:** sửa nhỏ (không đổi giá/danh mục/thông tin chính) không bắt buộc qua lại vòng duyệt — quy tắc cụ thể "thế nào là sửa lớn" cần được nhóm chốt và ghi rõ trong tài liệu kỹ thuật khi hiện thực (gợi ý: đổi giá, đổi danh mục, đổi tên → cần duyệt lại; đổi mô tả nhỏ, đổi ảnh → không cần).

---

## 8. Flash Sale Lifecycle

Áp dụng cho ADM-19, BON-14.

```
Admin tạo Flash Sale: khung giờ + danh sách sản phẩm + giá sale + số lượng giới hạn
      │
      ▼
Celery beat kiểm tra theo lịch:
      │
      ├── Đến giờ bắt đầu ──► kích hoạt: sản phẩm hiển thị giá sale, đếm ngược trên trang chủ
      │
      ├── Trong khung giờ, mỗi lần đặt hàng:
      │        atomic decrement số lượng sale còn lại (F() expression / Redis atomic)
      │        │
      │        └── Hết số lượng sale ──► sản phẩm tự động trả về giá gốc NGAY (không đợi hết giờ)
      │
      └── Đến giờ kết thúc ──► tự động trả toàn bộ sản phẩm còn lại về giá gốc
```

Nếu bật realtime (BON-14): số lượng còn lại broadcast qua WebSocket để FE cập nhật thanh tiến trình "đã bán x%" không cần reload.

---

## 9. Wallet / Points Transaction Flow (nếu triển khai Bonus loyalty)

Áp dụng cho BON-06..07.

```
Sự kiện phát sinh (đơn hoàn thành, hủy/hoàn đơn...)
      │
      ▼
WalletService / PointService (điểm truy cập DUY NHẤT thay đổi số dư)
      │
      ▼
transaction.atomic() + khóa dòng số dư
      │
      ▼
Ghi WalletTransaction / PointTransaction (append-only)
      │
      ▼
Cập nhật số dư hiển thị (denormalize từ tổng các transaction, hoặc cột balance được cập nhật trong CÙNG transaction)
```

Không có luồng nào khác được phép sửa trực tiếp cột `balance`/`points` ngoài luồng này (xem `PROJECT_CONSTITUTION.md` mục 8, `business_rules.md` BR-INV-03 áp dụng tương tự cho ví/điểm).

---

## Tài liệu liên quan

- `business_rules.md` — các ràng buộc chi tiết áp dụng tại từng bước chuyển trạng thái ở trên.
- `use_cases.md` — kịch bản sử dụng cụ thể tương ứng với từng workflow.
- `modules.md`, `roles.md` — bối cảnh module/vai trò liên quan tới từng luồng.
- `ARCHITECTURE.md` (mục 7, 9) — cách các luồng có yêu cầu concurrency (Order, Flash Sale, Wallet) được đảm bảo đúng ở tầng kỹ thuật.
