# Roles

Tài liệu mô tả các vai trò người dùng trong hệ thống, quyền hạn, và ranh giới dữ liệu của từng vai trò. Đây là tài liệu nghiệp vụ — quy tắc kỹ thuật để hiện thực phân quyền xem ở `ARCHITECTURE.md` (mục 4, 8) và `CODING_STANDARDS.md` (mục 8).

## 1. Tổng quan 3 vai trò

| Vai trò | Mã | Mô tả | Phạm vi dữ liệu |
|---|---|---|---|
| **Admin hệ thống** | `ADMIN` | Quản trị toàn sàn | Toàn bộ dữ liệu hệ thống |
| **Nhà bán hàng (Seller)** | `SELLER` | Quản lý một gian hàng | Chỉ dữ liệu thuộc gian hàng của chính mình |
| **Khách hàng (Customer)** | `CUSTOMER` | Mua sắm trên sàn | Chỉ dữ liệu cá nhân (đơn hàng, giỏ hàng, đánh giá... của chính mình) |

Một tài khoản (`User`) tại một thời điểm gắn với đúng một vai trò chính. `Customer` có thể đăng ký trở thành `Seller` (SEL-18) — khi đó tài khoản có thêm `SellerProfile`, nhưng vai trò `CUSTOMER` gốc vẫn giữ nguyên (một người vừa mua vừa bán).

## 2. Admin hệ thống

### 2.1 Mô tả
Quản trị toàn sàn: người dùng, seller, sản phẩm, đơn hàng, khuyến mãi, báo cáo.

### 2.2 Quyền hạn chính

| Nhóm quyền | Chi tiết | Mã YC liên quan |
|---|---|---|
| Xem báo cáo tổng quan | Dashboard toàn sàn, biểu đồ doanh thu, top sản phẩm | ADM-01..03 |
| Quản lý khách hàng | CRUD, khóa/mở khóa, reset mật khẩu | ADM-04, ADM-06, ADM-07 |
| Quản lý seller | CRUD, duyệt đăng ký, xác minh giấy tờ, khóa gian hàng, theo dõi doanh thu | ADM-05, ADM-09..12 |
| Phân quyền | Gán/thu hồi vai trò | ADM-08 |
| Quản lý sản phẩm toàn sàn | Duyệt sản phẩm, ẩn/xóa sản phẩm vi phạm, quản lý danh mục & thương hiệu | ADM-13..16 |
| Quản lý đơn hàng toàn sàn | Theo dõi mọi đơn, xử lý tranh chấp/khiếu nại | ADM-17..18 |
| Khuyến mãi cấp sàn | Flash Sale, Coupon toàn sàn, Banner | ADM-19..21 |
| Báo cáo | Top seller/khách hàng/danh mục, tỷ lệ hoàn/hủy, xuất Excel/PDF | ADM-22..24 |
| Hệ thống | Audit Log, cấu hình hệ thống (phí sàn, feature flag) | ADM-25..26 |

### 2.3 Ranh giới
- Admin **không** trực tiếp tạo/sửa sản phẩm của seller — chỉ duyệt, ẩn, hoặc yêu cầu chỉnh sửa.
- Mọi hành động nhạy cảm của Admin (khóa tài khoản, duyệt seller, đổi quyền, sửa/xóa sản phẩm người khác) **bắt buộc** ghi Audit Log.

## 3. Nhà bán hàng (Seller)

### 3.1 Mô tả
Quản lý gian hàng: sản phẩm, kho, đơn hàng, voucher shop, chat với khách.

### 3.2 Vòng đời trở thành Seller
```
Customer đăng ký bán hàng (SEL-18)
    → điền thông tin shop, upload giấy tờ
    → hồ sơ ở trạng thái "pending"
    → Admin duyệt (ADM-09)
    → approved → SellerProfile được kích hoạt, có thể tạo sản phẩm
    → rejected → Customer nhận thông báo lý do, có thể nộp lại
```

### 3.3 Quyền hạn chính

| Nhóm quyền | Chi tiết | Mã YC liên quan |
|---|---|---|
| Dashboard | Thống kê riêng của shop mình | SEL-01 |
| Quản lý sản phẩm | CRUD, upload ảnh/video, biến thể (size/màu), SKU/barcode | SEL-02..05 |
| Quản lý kho | Nhập/xuất/điều chỉnh tồn, lịch sử, cảnh báo sắp hết hàng | SEL-06..09 |
| Quản lý đơn hàng | Xử lý luồng trạng thái đơn (thuộc shop mình), in phiếu giao | SEL-10..11 |
| Voucher | Tạo voucher riêng của shop | SEL-12 |
| Khách hàng | Xem danh sách khách đã mua tại shop mình | SEL-13 |
| Đánh giá | Trả lời review, báo cáo review vi phạm | SEL-14..15 |
| Chat | Nhắn tin với khách hàng | SEL-16 |
| Hồ sơ shop | Trang gian hàng công khai, đăng ký bán hàng | SEL-17..18 |

### 3.4 Ranh giới (quan trọng nhất của vai trò này)
- **Seller chỉ được thao tác dữ liệu thuộc gian hàng của chính mình** — sản phẩm, đơn hàng, kho, voucher, khách hàng đều phải scope theo `shop_id` của seller đang đăng nhập. Đây là ranh giới bảo mật cốt lõi của mô hình multi-vendor (xem `ARCHITECTURE.md` mục 8).
- Sản phẩm mới/sửa lớn phải qua Admin duyệt trước khi hiển thị công khai (ADM-13) — Seller không có toàn quyền publish ngay lập tức.
- Seller không thể tự mở khóa gian hàng của mình khi đã bị Admin khóa (ADM-11).

## 4. Khách hàng (Customer)

### 4.1 Mô tả
Mua sắm: tìm kiếm, giỏ hàng, đặt hàng, thanh toán, đánh giá, chat với shop.

### 4.2 Quyền hạn chính

| Nhóm quyền | Chi tiết | Mã YC liên quan |
|---|---|---|
| Tài khoản | Đăng ký, đăng nhập/đăng xuất, Google Login, quên mật khẩu, hồ sơ cá nhân, sổ địa chỉ | CUS-01..06 |
| Duyệt mua | Trang chủ, tìm kiếm & lọc, chi tiết sản phẩm, review & Q&A | CUS-07..11 |
| Wishlist | Thêm/bỏ yêu thích | CUS-12 |
| Giỏ hàng & Thanh toán | Quản lý giỏ, checkout, phương thức thanh toán | CUS-13..15 |
| Đơn hàng | Theo dõi, hủy đơn, mua lại, yêu cầu trả hàng/hoàn tiền | CUS-16..18 |
| Đánh giá | Viết đánh giá sau khi nhận hàng | CUS-19 |
| Chat & Thông báo | Chat với shop, trung tâm thông báo | CUS-20..21 |

### 4.3 Ranh giới
- Customer chỉ xem/sửa được **đơn hàng, giỏ hàng, địa chỉ, đánh giá của chính mình** — không có endpoint nào cho phép truy cập dữ liệu của customer khác qua đổi ID.
- Chỉ được đánh giá sản phẩm đã mua và đơn đã hoàn thành (verified purchase — CUS-11, CUS-19).
- Chỉ được hủy đơn khi đơn ở trạng thái hợp lệ (chưa xác nhận) — không hủy tùy ý ở mọi trạng thái (CUS-17).

## 5. Ma trận quyền theo module (tóm tắt)

| Module | Admin | Seller | Customer |
|---|:---:|:---:|:---:|
| Quản lý người dùng | Toàn quyền | — | Chỉ hồ sơ bản thân |
| Quản lý seller/gian hàng | Duyệt/khóa | Quản lý shop mình | Đăng ký trở thành seller |
| Sản phẩm | Duyệt/ẩn/xóa vi phạm | CRUD trong shop mình | Chỉ xem |
| Kho | Chỉ xem báo cáo | Toàn quyền trong shop mình | — |
| Đơn hàng | Xem toàn sàn, xử lý tranh chấp | Xử lý đơn thuộc shop mình | Đặt/hủy/theo dõi đơn của mình |
| Khuyến mãi | Cấp sàn (Flash Sale, Coupon, Banner) | Cấp shop (voucher riêng) | Sử dụng khi checkout |
| Đánh giá | Xử lý báo cáo vi phạm | Trả lời review | Viết review |
| Chat | — | Chat với khách | Chat với shop |
| Báo cáo | Toàn sàn | Riêng shop mình | — |
| Cấu hình hệ thống | Toàn quyền | — | — |

## 6. Tài liệu liên quan

- `modules.md` — chi tiết từng module chức năng theo vai trò trên.
- `use_cases.md` — kịch bản sử dụng cụ thể cho từng vai trò.
- `business_rules.md` — quy tắc nghiệp vụ chi tiết áp dụng khi thực thi quyền hạn.
- `ARCHITECTURE.md` (mục 4, 8) — cách hiện thực phân quyền & multi-tenant isolation ở tầng kỹ thuật.
