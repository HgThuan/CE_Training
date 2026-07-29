# Sprint 05 — Storefront, Search & Discovery

Tài liệu này ghi lại các quyết định triển khai của Sprint 05. Phạm vi thực thi chi tiết nằm
trong `plansprint05.md`; các nguyên tắc của `PROJECT_CONSTITUTION.md` vẫn có mức ưu tiên cao nhất.

## Quyết định kiến trúc

- Dùng `apps.storefront` cho Banner và Home aggregation.
- Dùng `apps.engagement` cho Product Q&A, Wishlist và Follow Shop.
- Mở rộng feature frontend `product` cho trang chi tiết thay vì tạo bounded context mới.
- Dùng `apps.ai` làm AI service layer, mọi lời gọi provider phải đi qua `AIService`.
- Giữ page-number pagination (`page`, `page_size`) để tương thích API hiện hữu.
- Giữ các query param Product hiện hữu và hỗ trợ alias của Search API để không phá client cũ.
- Full-text search dùng PostgreSQL config `simple` kết hợp `pg_trgm`. PostgreSQL không cung cấp
  config `vietnamese` mặc định; việc bổ sung tokenizer tiếng Việt chuyên dụng được tách thành
  một cải tiến có benchmark.
- Banner nhận `image_url`. Upload file banner chưa có storage contract riêng nên không được giả
  lập bằng dữ liệu base64.
- Các nhánh Sprint được xếp chồng A → F. Nhánh review tổng hợp trỏ tới kết quả sau Part F.

## Part C — Product detail và Q&A

- Q&A được đặt trong `apps.engagement`; product catalog chỉ cung cấp selector xác định sản phẩm
  public hợp lệ.
- Customer đang hoạt động được đặt câu hỏi. Chỉ Seller đang hoạt động sở hữu shop của sản phẩm
  được trả lời; public API chỉ trả câu hỏi `visible`.
- Quan hệ one-to-one và `select_for_update()` bảo vệ thao tác trả lời đồng thời. Payload tác giả
  không lộ email, số điện thoại hoặc dữ liệu profile riêng.
- Frontend mở rộng `features/product`: breadcrumb, gallery có thumbnail/video/lightbox, lựa chọn
  biến thể (kể cả biến thể hết hàng để đăng ký waitlist), tab Description/Q&A/Reviews, skeleton,
  retry và chống response cũ ghi đè khi đổi route.
- Hash `#description`, `#qa`, `#reviews` là deep link ổn định; khách chưa đăng nhập quay lại đúng
  tab Q&A sau luồng login.

## Nguyên tắc tương thích và fallback

- PostgreSQL + `pg_trgm`/`pgvector` là runtime mục tiêu. Test SQLite dùng keyword fallback và
  không được dùng để xác nhận hiệu năng/vector index.
- Redis là lớp tối ưu, không phải nguồn dữ liệu. Cache lỗi phải fallback về database.
- AI search/recommendation phải fallback về keyword/best-seller khi feature flag tắt, provider
  timeout hoặc vector chưa được index.
- Product public luôn được lọc theo trạng thái Product, Shop, Category và tồn kho; kết quả AI
  không được bỏ qua các điều kiện này.
- Cache key phải deterministic, gồm đầy đủ query/context và không dùng `hash()` của Python.

## Bảo mật

- Không đưa credential từ tài liệu kế hoạch vào source code, migration, test fixture hoặc log.
- Chỉ khai báo tên biến trong `.env.example`; secret thật chỉ nằm trong `.env` bị ignore.
- Prompt, response và lỗi provider được giới hạn/mask trước khi lưu `AIRequestLog`.
- AI endpoint áp dụng rate limit riêng cho anonymous và authenticated user.

## Điều kiện vận hành PostgreSQL

Database user của môi trường triển khai cần quyền tạo hoặc sử dụng các extension:

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS vector;
```

Nếu database user không có quyền `CREATE EXTENSION`, DBA phải cài extension trước khi chạy
migration. HNSW index chỉ được tạo trên PostgreSQL có `pgvector`; test SQLite không tạo index này.

## Phạm vi traceability

Sprint này hoàn thành các slice được nêu trong kế hoạch Sprint 05. Một số acceptance criteria
rộng hơn trong workbook nguồn chưa nằm trong kế hoạch rút gọn và không được đánh dấu hoàn tất:

- Flash Sale countdown và notification khi shop có sản phẩm mới.
- Review thật, filter review theo sao/media (Sprint 08); Sprint này chỉ có Q&A và placeholder.
- Filter theo mọi thuộc tính động (màu/kích thước).
- Lịch sử mua/cart làm signal recommendation khi các module đó chưa tồn tại.
- Benchmark SLA `<500 ms` trên seed tối thiểu 10.000 sản phẩm trong PostgreSQL production-like.
- Trang lỗi 404/500 và SEO metadata đầy đủ cho toàn site.

Các mục trên cần backlog/test plan riêng trước khi đóng toàn bộ requirement ID gốc.

## Nhánh và thứ tự merge

1. `feature/admin-banners`
2. `feature/CUS_search-filter-cache`
3. `feature/CUS_product-detail-qa`
4. `feature/CUS_wishlist-follow-responsive`
5. `feature/Aiservice-search`
6. `feature/Ai-recommendation`
7. `review/sprint-05-complete` chỉ phục vụ review tích hợp

Không push nhánh tự động. Mỗi lần push cần người dùng review diff, kết quả kiểm thử và phê duyệt
riêng theo `AGENTS.md`.
