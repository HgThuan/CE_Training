# Modules

Tài liệu liệt kê các module chức năng của hệ thống, nhóm theo lĩnh vực nghiệp vụ (không theo vai trò như `roles.md`, mà theo domain — vì nhiều module được nhiều vai trò cùng dùng chung, ví dụ Order, Chat). Mỗi module nên tương ứng với một Django app / một feature folder ở Frontend (xem `ARCHITECTURE.md`).

## Bảng tổng hợp module

| # | Module | Domain app gợi ý | Vai trò liên quan | Mã YC chính |
|---|---|---|---|---|
| 1 | Account & Auth | `apps/account` | Cả 3 | CUS-01..06, ADM-06..08, NFR-01 |
| 2 | Seller Onboarding | `apps/seller_onboarding` | Admin, Seller | SEL-18, ADM-09..10 |
| 3 | Catalog (Danh mục, Thương hiệu) | `apps/catalog` | Admin, Seller (đọc), Customer (đọc) | ADM-15..16 |
| 4 | Product (Sản phẩm & Biến thể) | `apps/product` | Seller, Admin (duyệt), Customer (đọc) | SEL-02..05, ADM-13..14, CUS-10 |
| 5 | Inventory (Kho) | `apps/inventory` | Seller | SEL-06..09 |
| 6 | Shop (Gian hàng) | `apps/shop` | Seller, Admin, Customer (đọc) | SEL-17, ADM-05, ADM-11..12 |
| 7 | Cart (Giỏ hàng) | `apps/cart` | Customer | CUS-13 |
| 8 | Order (Đơn hàng) | `apps/order` | Customer, Seller, Admin | CUS-14, CUS-16..18, SEL-10..11, ADM-17..18 |
| 9 | Payment (Thanh toán) | `apps/payment` | Customer, hệ thống | CUS-15 |
| 10 | Promotion (Khuyến mãi) | `apps/promotion` | Admin (sàn), Seller (shop), Customer (dùng) | ADM-19..21, SEL-12 |
| 11 | Review & Q&A | `apps/review` | Customer, Seller, Admin | CUS-11, CUS-19, SEL-14..15 |
| 12 | Wishlist | `apps/wishlist` | Customer | CUS-12 |
| 13 | Search & Discovery | `apps/search` | Customer | CUS-08..09, CUS-07 |
| 14 | Chat | `apps/chat` | Seller, Customer | SEL-16, CUS-20 |
| 15 | Notification | `apps/notification` | Cả 3 | CUS-21, BON-08 |
| 16 | Report & Analytics | `apps/report` | Admin, Seller | ADM-01..03, ADM-22..24, SEL-01 |
| 17 | Audit Log | `apps/audit` | Admin | ADM-25 |
| 18 | System Config | `apps/system_config` | Admin | ADM-26 |
| 19 | AI Service | `apps/ai_service` | Cả 3 (qua các module khác) | AI-01..15 |
| 20 | Bonus Features | nhiều app nhỏ | Tùy tính năng | BON-01..14 |

---

## 1. Account & Auth

Quản lý tài khoản, xác thực, phân quyền cho cả 3 vai trò.

**Chức năng:** đăng ký, đăng nhập/đăng xuất (JWT), Google Login, quên/đổi mật khẩu, hồ sơ cá nhân, sổ địa chỉ, khóa/mở khóa tài khoản, reset mật khẩu bởi Admin, RBAC.

**Phụ thuộc:** không phụ thuộc module khác — là module nền tảng, mọi module khác đều dùng để xác thực & phân quyền.

## 2. Seller Onboarding

Quản lý vòng đời trở thành người bán, tách riêng khỏi module Shop vì có luồng duyệt riêng.

**Chức năng:** đăng ký bán hàng (form nhiều bước, upload giấy tờ), Admin duyệt/từ chối, xác minh thông tin gian hàng.

**Phụ thuộc:** Account & Auth (ai đăng ký), Shop (tạo `Shop` khi được duyệt).

## 3. Catalog (Danh mục & Thương hiệu)

Dữ liệu nền dùng chung toàn sàn.

**Chức năng:** CRUD danh mục đa cấp (cây), CRUD thương hiệu, gán thương hiệu cho sản phẩm.

**Phụ thuộc:** Product (Product tham chiếu Category & Brand).

## 4. Product (Sản phẩm & Biến thể)

Module trung tâm của toàn hệ thống.

**Chức năng:** CRUD sản phẩm, upload ảnh/video, biến thể (size/màu, SKU, barcode), luồng duyệt sản phẩm (draft → pending → approved/rejected), ẩn/xóa sản phẩm vi phạm.

**Phụ thuộc:** Catalog, Shop, Inventory (mỗi biến thể có tồn kho riêng), Search (index sau khi approved).

## 5. Inventory (Kho)

**Chức năng:** phiếu nhập kho, phiếu xuất/điều chỉnh tồn, lịch sử biến động (StockMovement append-only), cảnh báo sắp hết hàng.

**Phụ thuộc:** Product (biến thể nào cần quản lý tồn), Order (trừ tồn khi đặt hàng, hoàn tồn khi hủy).

**Ghi chú:** đây là module có yêu cầu concurrency cao nhất — xem `business_rules.md` và `ARCHITECTURE.md` mục 7.

## 6. Shop (Gian hàng)

**Chức năng:** trang gian hàng công khai, quản lý thông tin shop, khóa/mở khóa gian hàng (Admin), theo dõi doanh thu seller.

**Phụ thuộc:** Seller Onboarding (nguồn tạo Shop), Product (sản phẩm thuộc shop), Order (đơn hàng thuộc shop).

## 7. Cart (Giỏ hàng)

**Chức năng:** thêm/sửa/xóa sản phẩm trong giỏ, giỏ gộp theo shop, giỏ khách vãng lai (localStorage) merge khi đăng nhập, kiểm tra tồn kho & cảnh báo giá thay đổi.

**Phụ thuộc:** Product (giá & tồn kho hiện tại), Order (nguồn tạo đơn từ giỏ).

## 8. Order (Đơn hàng)

Module lõi của nghiệp vụ bán hàng, được cả 3 vai trò cùng thao tác ở các góc nhìn khác nhau.

**Chức năng:** checkout (tách đơn theo shop), luồng trạng thái đơn, hủy đơn & mua lại, yêu cầu trả hàng/hoàn tiền, xử lý tranh chấp, theo dõi đơn toàn hệ thống.

**Phụ thuộc:** Cart, Inventory, Promotion (áp voucher), Payment, Notification (bắn thông báo khi đổi trạng thái).

## 9. Payment (Thanh toán)

**Chức năng:** COD, tích hợp 1 cổng sandbox (VNPay/MoMo/Stripe test), xử lý callback/IPN, đối soát giao dịch.

**Phụ thuộc:** Order (một Order có thể có nhiều PaymentTransaction).

## 10. Promotion (Khuyến mãi)

**Chức năng:** Flash Sale (cấp sàn), Coupon cấp sàn, Voucher cấp shop, Banner trang chủ. Logic cộng dồn voucher sàn + shop ở checkout.

**Phụ thuộc:** Product (sản phẩm tham gia Flash Sale), Shop (voucher riêng của shop), Order (áp dụng khi checkout).

## 11. Review & Q&A

**Chức năng:** viết đánh giá (sau khi đơn hoàn thành, verified purchase), Q&A trên trang sản phẩm, seller trả lời review, báo cáo review vi phạm.

**Phụ thuộc:** Order (điều kiện được đánh giá), Product (review gắn với sản phẩm).

## 12. Wishlist

**Chức năng:** thêm/bỏ yêu thích, trang wishlist riêng, thông báo khi sản phẩm yêu thích giảm giá.

**Phụ thuộc:** Product, Notification.

## 13. Search & Discovery

**Chức năng:** tìm kiếm từ khóa (autocomplete), bộ lọc & sắp xếp đa tiêu chí, trang chủ (banner, Flash Sale, gợi ý, sản phẩm mới/bán chạy).

**Phụ thuộc:** Product (nguồn index), AI Service (smart search, semantic search khi bật).

## 14. Chat

**Chức năng:** nhắn tin realtime 2 chiều Seller ↔ Customer, gửi text/ảnh, đánh dấu đã đọc, gửi kèm link sản phẩm/đơn hàng.

**Phụ thuộc:** Account & Auth, kiến trúc Realtime (xem `ARCHITECTURE.md` mục 5).

## 15. Notification

**Chức năng:** trung tâm thông báo in-app, đếm chưa đọc, đẩy realtime qua WebSocket, fallback polling.

**Phụ thuộc:** hầu hết module khác đều là nguồn phát thông báo (Order, Promotion, Review, Chat...).

## 16. Report & Analytics

**Chức năng:** dashboard Admin/Seller, top sản phẩm/seller/khách hàng, tỷ lệ hoàn/hủy, xuất Excel/PDF, AI Sales Analytics.

**Phụ thuộc:** Order, Product, Shop (nguồn dữ liệu tổng hợp), AI Service (diễn giải số liệu).

## 17. Audit Log

**Chức năng:** ghi lại hành động nhạy cảm (khóa tài khoản, duyệt seller, sửa/xóa sản phẩm, đổi quyền), màn hình tra cứu có bộ lọc.

**Phụ thuộc:** middleware/signal gắn vào các module có hành động nhạy cảm.

## 18. System Config

**Chức năng:** cấu hình tham số chung (phí sàn %, ngưỡng cảnh báo tồn kho mặc định, feature flag).

**Phụ thuộc:** đọc bởi nhiều module (Order tính phí sàn, Inventory lấy ngưỡng mặc định...).

## 19. AI Service

Module hạ tầng dùng chung, không lộ diện trực tiếp cho người dùng mà được các module khác gọi tới.

**Chức năng:** Smart Search, Semantic Search, Recommendation, Similar Products, Shopping Assistant (chatbot), Customer Support tự động, Review Summary, Product Summary, Compare, Generate Description, Auto Tag, Translate, Price Suggestion, Sales Analytics.

**Phụ thuộc:** Product, Order, Review (nguồn dữ liệu cho các tính năng AI). Kiến trúc chi tiết xem `ARCHITECTURE.md` mục 6.

## 20. Bonus Features

Nhóm tính năng điểm cộng, độc lập tương đối, có thể triển khai sau khi các module Bắt buộc đã hoàn thành:

- Theo dõi vận chuyển (BON-01)
- Follow shop (BON-02)
- Combo sản phẩm / Mua kèm giảm giá (BON-03..04)
- Affiliate (BON-05)
- Loyalty: điểm thưởng, ví điện tử (BON-06..07)
- Thông báo realtime nâng cao (BON-08)
- Waitlist hết hàng (BON-09)
- Báo cáo vi phạm (BON-10)
- Import/Export Excel (BON-11)
- QR đơn hàng & sản phẩm (BON-12)
- Xu hướng sản phẩm (BON-13)
- Flash Sale realtime (BON-14)

## Sơ đồ phụ thuộc module (tổng quan)

```
Account & Auth ─────────────────────────────────────────► (mọi module)
     │
     ▼
Seller Onboarding ──► Shop ──► Catalog ──► Product ──► Inventory
                                              │
                                              ▼
                        Cart ──► Order ──► Payment
                          │         │
                          ▼         ▼
                     Promotion   Review & Q&A / Wishlist
                                     │
                                     ▼
                              Notification ◄── Chat
                                     │
Report & Analytics ◄── (Order, Product, Shop) ──► AI Service
Audit Log ◄── (hành động nhạy cảm ở mọi module)
System Config ──► (đọc bởi nhiều module)
```

## Tài liệu liên quan

- `roles.md` — vai trò nào thao tác trên module nào.
- `use_cases.md` — kịch bản sử dụng cụ thể trong từng module.
- `business_rules.md` — quy tắc nghiệp vụ áp dụng trong từng module.
- `workflows.md` — luồng trạng thái chi tiết của các module có state machine (Order, Seller Onboarding, Product, Return/Dispute).
- `ARCHITECTURE.md` — cấu trúc kỹ thuật tương ứng với từng module (Django app).
