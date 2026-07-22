# AGILE PROJECT PLAN — 1 MONTH SOLO EDITION

## Multi-Vendor AI E-commerce Platform

> **Thời gian thực hiện:** 22/07/2026 – 20/08/2026  
> **Múi giờ:** Asia/Bangkok (UTC+7)  
> **Hình thức:** Dự án cá nhân  
> **Phạm vi cam kết:** Toàn bộ 111 yêu cầu trong file đặc tả, bao gồm Bắt buộc, Nên có, Tùy chọn và Phi chức năng  
> **Ngày hoàn thành cuối cùng:** 20/08/2026 lúc 23:59

---

# 1. Mục tiêu tài liệu

Tài liệu này xác định cách triển khai dự án **Multi-Vendor AI E-commerce Platform** theo Agile/Scrum trong thời gian một tháng, phù hợp với một cá nhân đảm nhiệm toàn bộ vai trò:

- phân tích nghiệp vụ;
- thiết kế hệ thống;
- thiết kế cơ sở dữ liệu;
- phát triển Backend;
- phát triển Frontend;
- kiểm thử;
- tích hợp AI;
- DevOps;
- viết tài liệu;
- chuẩn bị dữ liệu và kịch bản demo.

Tài liệu cung cấp:

- Product Goal và phạm vi cố định;
- Product Backlog theo Epic;
- lịch Sprint có ngày bắt đầu và deadline cụ thể;
- phân bổ toàn bộ nhóm yêu cầu vào Sprint;
- cách tổ chức Scrum tinh gọn cho dự án cá nhân;
- Definition of Ready và Definition of Done;
- chiến lược kiểm thử, Git, CI/CD và tài liệu;
- checkpoint hằng ngày và tiêu chí đóng Sprint;
- cơ chế kiểm soát tiến độ khi phạm vi không được phép cắt giảm.

---

# 2. Product Vision và phạm vi

## 2.1. Product Vision

Xây dựng một nền tảng thương mại điện tử đa gian hàng có ba vai trò:

- Admin;
- Seller;
- Customer.

Hệ thống phải hỗ trợ đầy đủ:

- xác thực và phân quyền;
- đăng ký và phê duyệt Seller;
- quản lý shop;
- danh mục, thương hiệu, sản phẩm, biến thể và media;
- nhập, xuất và kiểm soát tồn kho;
- storefront, tìm kiếm, lọc và wishlist;
- giỏ hàng nhiều shop;
- voucher cấp sàn và cấp shop;
- checkout nhiều shop;
- COD và thanh toán sandbox;
- quản lý vòng đời đơn hàng;
- review, Q&A, trả hàng và tranh chấp;
- chat và thông báo realtime;
- dashboard và báo cáo;
- các tính năng AI;
- các tính năng Bonus;
- bảo mật, hiệu năng, logging, testing, Docker, Nginx, CI/CD và backup.

AI phải được cô lập khỏi nghiệp vụ thương mại cốt lõi. Lỗi AI không được làm gián đoạn việc xem sản phẩm, đặt hàng, thanh toán hoặc xử lý đơn.

## 2.2. Thống kê phạm vi

| Nhóm | Tổng | Bắt buộc | Nên có | Tùy chọn |
|---|---:|---:|---:|---:|
| Admin | 26 | 16 | 8 | 2 |
| Seller | 18 | 14 | 4 | 0 |
| Customer | 22 | 19 | 2 | 1 |
| AI | 15 | 5 | 3 | 7 |
| Bonus | 14 | 0 | 2 | 12 |
| Phi chức năng | 16 | 11 | 4 | 1 |
| **Tổng** | **111** | **65** | **23** | **23** |

## 2.3. Nguyên tắc quản lý phạm vi cố định

Trong kế hoạch này:

- toàn bộ **111 yêu cầu** đều thuộc phạm vi Release 1.0;
- mức Bắt buộc/Nên có/Tùy chọn chỉ quyết định **thứ tự thực hiện**, không quyết định việc loại bỏ;
- không chuyển chức năng sang Phase 2;
- không thay use case đầy đủ bằng mock chỉ để demo;
- không bỏ qua yêu cầu phi chức năng;
- mỗi chức năng phải có Backend, Frontend, permission, error handling và test tương ứng;
- chức năng chưa đạt Definition of Done không được đánh dấu hoàn thành.

Do thời gian chỉ có 30 ngày, kế hoạch áp dụng:

- Sprint rất ngắn;
- làm việc liên tục cả cuối tuần;
- phát triển theo vertical slice;
- tái sử dụng component, serializer, service và test fixture;
- tự động hóa lint, test, migration check và build từ ngày đầu;
- giới hạn WIP để tránh nhiều chức năng dở dang;
- cập nhật tài liệu trong cùng ngày với code.

> Đây là lịch thực hiện có mức rủi ro rất cao đối với một cá nhân. Việc giữ toàn bộ phạm vi đồng nghĩa không có ngày dự phòng độc lập; mọi chậm trễ phải được xử lý ngay trong Sprint đang diễn ra hoặc trong Sprint 12.

---

# 3. Mô hình Agile cho dự án cá nhân

## 3.1. Framework

Sử dụng **Solo Scrum**, kết hợp các thực hành kỹ thuật của Extreme Programming:

- Product Backlog có thứ tự ưu tiên;
- User Story có Acceptance Criteria;
- phát triển theo vertical slice;
- test tự động;
- Continuous Integration;
- refactoring liên tục;
- trunk ổn định;
- release theo Increment có thể chạy;
- ghi Architecture Decision Record cho quyết định lớn.

## 3.2. Vai trò

Một người đảm nhiệm toàn bộ vai trò nhưng phải tách trách nhiệm theo từng thời điểm:

| Vai trò | Trách nhiệm trong dự án cá nhân |
|---|---|
| Product Owner | Quản lý Product Goal, ưu tiên backlog, chấp nhận User Story |
| Scrum Master | Giữ nhịp Sprint, phát hiện blocker, bảo vệ WIP limit |
| Business Analyst | Làm rõ yêu cầu, viết Acceptance Criteria và business rule |
| Architect | Chốt kiến trúc, database, API, concurrency và security |
| Backend Developer | Django, DRF, Celery, Channels, PostgreSQL |
| Frontend Developer | Vue 3, TypeScript, Pinia, Router, UI |
| QA | Viết test, chạy regression, kiểm thử thủ công |
| DevOps | Docker, Nginx, CI/CD, environment và backup |
| Technical Writer | Cập nhật README, OpenAPI, ERD, ADR và hướng dẫn demo |

Khi tự đánh giá một Story, phải đổi góc nhìn:

1. viết code với vai trò Developer;
2. nghỉ khỏi Story hoặc chuyển task ngắn khác;
3. quay lại với checklist QA;
4. kiểm tra requirement với vai trò Product Owner;
5. chỉ đóng Story khi DoD đạt.

## 3.3. Scrum Events tinh gọn

| Sự kiện | Tần suất | Thời lượng tối đa | Kết quả |
|---|---|---:|---|
| Sprint Planning | Đầu mỗi Sprint | 30 phút | Sprint Goal, Story, task, dependency |
| Daily Scrum | Mỗi sáng | 10 phút | Hôm qua, hôm nay, blocker |
| Mid-day Check | Mỗi ngày | 5 phút | Xác nhận còn bám Sprint Goal |
| Backlog Refinement | Cuối mỗi ngày | 15 phút | Story 2 Sprint kế tiếp đạt Ready |
| Sprint Review | Cuối Sprint | 30 phút | Demo Increment và kiểm tra Acceptance Criteria |
| Sprint Retrospective | Cuối Sprint | 15 phút | Giữ, bỏ, cải thiện cho Sprint sau |
| Release Checkpoint | Sau Sprint 2, 4, 7, 10, 12 | 45 phút | Smoke test và tạo tag release |

## 3.4. WIP Limit

- Tối đa **1 User Story chính** ở trạng thái In Progress.
- Có thể có thêm **1 task nền** đang chờ như Celery, build hoặc provider callback.
- Không mở Story mới khi Story hiện tại còn thiếu test hoặc tài liệu.
- Bug Critical/High chặn việc mở Story mới.
- Không để quá 2 migration chưa được hợp nhất.
- Không để Backend hoàn thành trước Frontend quá một Sprint.

---

# 4. Lịch dự án cố định

## 4.1. Khoảng thời gian

- **Bắt đầu:** Thứ Tư, 22/07/2026.
- **Kết thúc:** Thứ Năm, 20/08/2026.
- **Tổng cộng:** 30 ngày theo lịch.
- Lịch baseline sử dụng cả thứ Bảy và Chủ Nhật.
- Deadline mỗi Sprint là **16:59  của ngày kết thúc.

## 4.2. Lịch Sprint tổng quan

| Sprint | Thời gian | Số ngày | Deadline | Mục tiêu chính |
|---|---|---:|---|---|
| Sprint 0 | 22/07/2026 | 1 | 22/07 16:59 | Foundation, quyết định kiến trúc, CI skeleton |
| Sprint 1 | 23–24/07/2026 | 2 | 24/07 16:59 | Auth, profile, address |
| Sprint 2 | 25–26/07/2026 | 2 | 26/07 16:59 | RBAC, Admin user, Seller onboarding |
| Sprint 3 | 27–28/07/2026 | 2 | 28/07 16:59 | Catalog, product, variant, media |
| Sprint 4 | 29–30/07/2026 | 2 | 30/07 16:59 | Inventory, stock ledger, concurrency |
| Sprint 5 | 31/07–01/08/2026 | 2 | 01/08 16:59 | Storefront, search, discovery, AI search nền |
| Sprint 6 | 02–03/08/2026 | 2 | 03/08 16:59 | Cart, promotion, Flash Sale |
| Sprint 7 | 04–06/08/2026 | 3 | 06/08 16:59 | Checkout, payment, order lifecycle |
| Sprint 8 | 07–08/08/2026 | 2 | 08/08 16:59 | Review, return, dispute, shipping |
| Sprint 9 | 09–10/08/2026 | 2 | 10/08 16:59 | Chat, notification, realtime |
| Sprint 10 | 11–12/08/2026 | 2 | 12/08 16:59 | Dashboard, reports, admin operations |
| Sprint 11 | 13–15/08/2026 | 3 | 15/08 16:59 | Hoàn thiện toàn bộ AI |
| Sprint 12 | 16–20/08/2026 | 5 | 20/08 16:59 | Bonus còn lại, NFR, regression, deployment, handover |

---

# 5. Cấu trúc Product Backlog

## 5.1. Cấp độ công việc

```text
Product Goal
└── Epic
    └── Feature
        └── User Story
            └── Technical Task / Test Task / Documentation Task
```

## 5.2. Quy tắc mã hóa

| Loại | Định dạng | Ví dụ |
|---|---|---|
| Epic | `EP-XX` | `EP-07 Cart, Promotion & Checkout` |
| User Story | Giữ mã đặc tả | `CUS-14` |
| Technical Story | `TECH-XXX` | `TECH-018 Inventory locking` |
| Bug | `BUG-XXX` | `BUG-027 Duplicate callback` |
| Spike | `SPIKE-XXX` | `SPIKE-004 Embedding model` |
| Documentation | `DOC-XXX` | `DOC-012 Payment sequence` |
| Test | `TEST-XXX` | `TEST-021 Concurrent checkout` |

## 5.3. Cấu trúc User Story

```text
Là một <vai trò>,
tôi muốn <khả năng>,
để <giá trị nghiệp vụ>.
```

Mỗi Story phải có:

- mã yêu cầu;
- mô tả và giá trị nghiệp vụ;
- độ ưu tiên;
- Story Point;
- Acceptance Criteria;
- dependency;
- database/API/UI bị ảnh hưởng;
- permission;
- happy path;
- failure path;
- test case;
- tài liệu liên quan;
- Definition of Done checklist.

Story 13 SP trở lên phải chia thành vertical slice nhỏ nhưng vẫn giữ nguyên use case tổng thể.

---

# 6. Product Backlog theo Epic

## EP-01 — Project Foundation & Engineering System

Bao phủ nền tảng của NFR-04, NFR-08 đến NFR-13, NFR-15, NFR-16 và các technical task:

- repository và branching;
- Django/Vue skeleton;
- PostgreSQL, Redis và Celery;
- response/error format;
- OpenAPI;
- lint, type check, test skeleton;
- Docker development;
- GitHub Actions;
- structured logging;
- seed data và backup skeleton.

## EP-02 — Identity, Authentication & Authorization

Bao phủ:

- CUS-01 đến CUS-06;
- ADM-04 đến ADM-08;
- NFR-01 đến NFR-04.

Kết quả:

- đăng ký, xác minh email và Google OAuth;
- JWT access/refresh, rotation, blacklist;
- quên mật khẩu;
- hồ sơ và địa chỉ;
- RBAC;
- object permission;
- quản lý trạng thái tài khoản.

## EP-03 — Seller Onboarding & Shop

Bao phủ:

- SEL-17, SEL-18;
- ADM-05, ADM-09 đến ADM-11;
- NFR-02.

Kết quả:

- hồ sơ đăng ký Seller;
- upload giấy tờ;
- duyệt/từ chối;
- shop profile và shop public;
- khóa/mở shop;
- tenant isolation.

## EP-04 — Catalog & Product Management

Bao phủ:

- SEL-02 đến SEL-05;
- ADM-13 đến ADM-16;
- CUS-10;
- NFR-03, NFR-05, NFR-10.

Kết quả:

- category tree;
- brand;
- product;
- media;
- attribute và variant;
- SKU;
- duyệt, từ chối, ẩn và xóa mềm sản phẩm;
- public product API.

## EP-05 — Inventory

Bao phủ:

- SEL-06 đến SEL-09;
- BON-09;
- NFR-10, NFR-14.

Kết quả:

- phiếu nhập/xuất/điều chỉnh;
- StockService;
- StockMovement append-only;
- inventory reservation;
- cảnh báo tồn thấp và waitlist;
- test concurrent chống oversell.

## EP-06 — Storefront, Search & Discovery

Bao phủ:

- CUS-07 đến CUS-12;
- CUS-22 phần storefront;
- ADM-21;
- BON-02;
- AI-01 đến AI-04;
- NFR-05, NFR-06.

Kết quả:

- trang chủ, banner;
- tìm kiếm keyword, fuzzy và semantic;
- filter, sorting;
- recommendation;
- product detail;
- Q&A;
- wishlist;
- follow shop;
- responsive UI.

## EP-07 — Cart, Promotion & Flash Sale

Bao phủ:

- CUS-13;
- ADM-19, ADM-20;
- SEL-12;
- BON-03, BON-04, BON-14;
- NFR-05, NFR-14.

Kết quả:

- cart user và guest;
- merge cart;
- nhóm theo shop;
- voucher sàn/shop;
- bundle và add-on deal;
- Flash Sale và giới hạn số lượng;
- promotion calculation engine;
- concurrency cho quota.

## EP-08 — Checkout, Payment & Order Lifecycle

Bao phủ:

- CUS-14 đến CUS-17;
- SEL-10, SEL-11;
- ADM-17;
- BON-01;
- NFR-07, NFR-14, NFR-15.

Kết quả:

- checkout nhiều shop;
- order group và order theo shop;
- snapshot;
- reserve/trừ kho;
- COD và payment sandbox;
- callback idempotent;
- seller xử lý đơn;
- customer theo dõi, hủy và mua lại;
- shipping tracking;
- admin theo dõi toàn sàn.

## EP-09 — Review, Return & Trust

Bao phủ:

- CUS-18, CUS-19;
- SEL-13 đến SEL-15;
- ADM-18;
- BON-10.

Kết quả:

- verified-purchase review;
- media review;
- seller reply;
- customer list;
- moderation/report;
- return/refund;
- dispute và evidence.

## EP-10 — Chat & Notifications

Bao phủ:

- SEL-16;
- CUS-20, CUS-21;
- BON-08;
- phần realtime của BON-14;
- NFR-07.

Kết quả:

- WebSocket auth;
- conversation và message persistence;
- attachment/link;
- unread count;
- in-app notification;
- reconnect và polling fallback;
- realtime Flash Sale.

## EP-11 — Dashboard, Reports & Administration

Bao phủ:

- ADM-01 đến ADM-03;
- ADM-12;
- ADM-22 đến ADM-26;
- SEL-01;
- BON-11, BON-13;
- AI-14;
- NFR-06, NFR-15, NFR-16.

Kết quả:

- dashboard Admin/Seller;
- doanh thu, đơn, top product và trend;
- import/export Excel;
- audit log;
- site setting và feature flag;
- report;
- AI sales analytics;
- backup operations.

## EP-12 — AI Platform & Features

Bao phủ toàn bộ:

- AI-01 đến AI-15.

Yêu cầu kỹ thuật:

- provider abstraction;
- timeout, retry và backoff;
- token/cost/latency log;
- cache theo content hash;
- feature flag;
- Celery;
- fallback;
- semantic search;
- recommendation;
- chatbot;
- summary;
- comparison;
- description generation;
- auto-tag;
- translation;
- price suggestion;
- sales analytics.

## EP-13 — Bonus, Quality, Deployment & Handover

Bao phủ:

- BON-01 đến BON-14;
- NFR-01 đến NFR-16;
- toàn bộ sản phẩm bàn giao.

Kết quả:

- affiliate;
- loyalty;
- wallet;
- QR;
- performance và security hardening;
- test coverage;
- Docker/Nginx;
- CI/CD;
- backup/restore;
- seed data;
- README;
- OpenAPI;
- ERD;
- demo script.

---

# 7. Ước lượng và quản lý capacity cá nhân

## 7.1. Story Point

Sử dụng Fibonacci:

```text
1, 2, 3, 5, 8, 13
```

| Độ khó ban đầu | Story Point |
|---|---:|
| Dễ | 3 |
| Trung bình | 5 |
| Khó | 8 |

Story Point dùng để:

- so sánh độ phức tạp;
- phát hiện Story quá lớn;
- theo dõi lệch kế hoạch;
- không quy đổi cứng thành số giờ.

Do Sprint chỉ dài 1–5 ngày, một Story 8 SP phải chia thành các slice Backend/API, Frontend/UI, test và tích hợp nhưng chỉ được đóng khi toàn use case hoàn tất.

## 7.2. Daily capacity

Baseline mỗi ngày:

| Khối công việc | Tỷ lệ |
|---|---:|
| Phát triển chức năng | 55% |
| Test và sửa lỗi | 20% |
| Thiết kế/refactor | 10% |
| Tài liệu | 10% |
| Planning và theo dõi | 5% |

Không dồn test và tài liệu sang cuối tháng.

## 7.3. Quy tắc xử lý chậm tiến độ

Vì không được giảm phạm vi:

1. Dừng mở Story mới.
2. Xử lý blocker và bug Critical/High trước.
3. Giảm refactor không thiết yếu nhưng không bỏ security/concurrency/test.
4. Tái sử dụng component/service/fixture.
5. Chuyển phần hoàn thiện UI thẩm mỹ sang cuối Sprint nhưng vẫn giữ đủ luồng.
6. Dùng Sprint 12 để hấp thụ phần việc trễ.
7. Ghi rõ carry-over trong Sprint Review; không đánh dấu Done giả.

---

# 8. Sprint Roadmap có deadline chi tiết

## Sprint 0 — Inception & Engineering Foundation

**Thời gian:** 22/07/2026  
**Deadline:** 22/07/2026 lúc 16:59  
**Sprint Goal:** tạo nền tảng đủ để phát triển, kiểm thử và triển khai liên tục.

### Phạm vi

- chốt Tailwind/Bootstrap, icon, chart library;
- chốt PK strategy;
- chốt OrderGroup/Order/Payment;
- chốt inventory reservation;
- chọn payment sandbox;
- chọn AI provider và embedding model;
- chọn media storage;
- tạo repository, branch và issue template;
- Django/Vue skeleton;
- PostgreSQL, pgvector, pg_trgm, Redis;
- Celery và Channels skeleton;
- lint, format, type check;
- pytest/vitest skeleton;
- GitHub Actions;
- Docker development;
- response/error format;
- OpenAPI;
- backlog đủ Ready đến Sprint 2;
- seed ba tài khoản mẫu.

### Deadline theo ngày

| Ngày | Kết quả phải đạt |
|---|---|
| 22/07 | Repository chạy được, CI xanh, ADR-001 đến ADR-006 có quyết định, backlog S1–S2 Ready |

### Exit Criteria

- `docker compose up` chạy stack development;
- Backend health check và Frontend render;
- migration đầu tiên chạy được;
- CI lint/test/build pass;
- không còn quyết định kiến trúc chặn Sprint 1.

---

## Sprint 1 — Authentication & User Foundation

**Thời gian:** 23–24/07/2026  
**Deadline:** 24/07/2026 lúc 16:59  
**Sprint Goal:** hoàn thành toàn bộ tài khoản Customer và nền tảng xác thực.

### Yêu cầu

- CUS-01 đến CUS-06;
- NFR-01, NFR-03, NFR-04;
- phần liên quan NFR-08, NFR-09.

### Ngày 23/07

- User/Profile/Address model và migration;
- đăng ký, xác minh email;
- đăng nhập JWT;
- refresh rotation và blacklist;
- Google OAuth;
- test auth service/API.

### Ngày 24/07

- quên/đặt lại mật khẩu;
- API `/me`;
- cập nhật hồ sơ;
- CRUD địa chỉ và duy nhất một địa chỉ mặc định;
- Pinia auth store;
- Axios interceptor;
- route guard;
- màn hình auth/profile/address;
- OpenAPI và regression.

### Exit Criteria

```text
Đăng ký → xác minh → đăng nhập thường/Google
→ refresh → sửa hồ sơ → quản lý địa chỉ
→ quên mật khẩu → logout
```

---

## Sprint 2 — RBAC, Admin User Management & Seller Onboarding

**Thời gian:** 25–26/07/2026  
**Deadline:** 26/07/2026 lúc 16:59  
**Sprint Goal:** hoàn thành ba vai trò, quản lý tài khoản và quy trình tạo shop.

### Yêu cầu

- ADM-04 đến ADM-11;
- SEL-17, SEL-18;
- NFR-02;
- NFR-15 phần audit cơ bản.

### Ngày 25/07

- role và permission classes;
- object-level permission;
- Admin list/search/filter user;
- khóa/mở/xóa mềm user;
- seller application và document;
- audit action.

### Ngày 26/07

- Admin duyệt/từ chối Seller;
- tạo SellerProfile và Shop;
- quản lý trạng thái shop;
- Seller cập nhật shop;
- shop public;
- UI Admin/Seller;
- test Seller A không đọc/sửa Seller B;
- smoke test Release 0.1.

### Release Checkpoint

**Release 0.1 — Foundation**, deadline 26/07/2026.

---

## Sprint 3 — Catalog & Product Management

**Thời gian:** 27–28/07/2026  
**Deadline:** 28/07/2026 lúc 16:59  
**Sprint Goal:** Seller quản lý catalog đầy đủ và Customer xem được sản phẩm.

### Yêu cầu

- SEL-02 đến SEL-05;
- ADM-13 đến ADM-16;
- CUS-10;
- NFR-03, NFR-05, NFR-10.

### Ngày 27/07

- Category tree và Brand;
- Product, ProductMedia;
- Attribute, AttributeValue;
- ProductVariant và SKU constraint;
- upload validation;
- Seller product CRUD.

### Ngày 28/07

- quy trình draft/pending/approved/rejected;
- Admin duyệt/từ chối/ẩn;
- soft delete;
- public list/detail;
- pagination/filter/sort;
- Product UI Seller/Admin/Customer;
- query optimization;
- API và permission test.

---

## Sprint 4 — Inventory & Availability

**Thời gian:** 29–30/07/2026  
**Deadline:** 30/07/2026 lúc 16:59  
**Sprint Goal:** toàn bộ thay đổi kho được kiểm soát, có lịch sử và chống oversell.

### Yêu cầu

- SEL-06 đến SEL-09;
- BON-09;
- NFR-10, NFR-14.

### Ngày 29/07

- InventoryBalance/StockMovement;
- StockEntry/StockEntryItem;
- StockService duy nhất;
- nhập, xuất, điều chỉnh;
- row lock/F expression;
- DB CheckConstraint.

### Ngày 30/07

- inventory reservation;
- low-stock threshold;
- waitlist hết hàng;
- màn hình kho;
- lịch sử giao dịch kho;
- concurrent test;
- rollback test;
- smoke test Release 0.2.

### Release Checkpoint

**Release 0.2 — Catalog & Inventory**, deadline 30/07/2026.

---

## Sprint 5 — Storefront, Search & Discovery

**Thời gian:** 31/07–01/08/2026  
**Deadline:** 01/08/2026 lúc 16:59  
**Sprint Goal:** Customer khám phá, tìm kiếm và lưu sản phẩm bằng cả tìm kiếm truyền thống và AI.

### Yêu cầu

- CUS-07 đến CUS-12;
- CUS-22 phần storefront;
- ADM-21;
- BON-02;
- AI-01 đến AI-04;
- NFR-05, NFR-06.

### Ngày 31/07

- home/banner;
- keyword/fuzzy search;
- filter và sorting;
- category/shop page;
- Q&A;
- wishlist;
- follow shop;
- responsive layout.

### Ngày 01/08

- AIService skeleton;
- embedding indexing;
- semantic search;
- recommendation;
- search cache;
- fallback sang keyword search;
- UI search/recommendation;
- test provider failure;
- OpenAPI và regression.

---

## Sprint 6 — Cart, Voucher, Bundle & Flash Sale

**Thời gian:** 02–03/08/2026  
**Deadline:** 03/08/2026 lúc 16:59  
**Sprint Goal:** Customer có giỏ hàng nhiều shop và promotion engine đầy đủ.

### Yêu cầu

- CUS-13;
- ADM-19, ADM-20;
- SEL-12;
- BON-03, BON-04, BON-14 phần Flash Sale;
- NFR-05, NFR-14.

### Ngày 02/08

- Cart/CartItem;
- guest cart;
- merge cart;
- chọn item checkout;
- nhóm theo shop;
- price preview;
- voucher platform/shop;
- usage quota.

### Ngày 03/08

- Bundle và BundleItem;
- Add-on Deal;
- Flash Sale và item;
- quota concurrency;
- promotion calculation service;
- cart/promotion UI;
- test stacking, expiry, scope và duplicate usage.

---

## Sprint 7 — Checkout, Payment & Order Lifecycle

**Thời gian:** 04–06/08/2026  
**Deadline:** 06/08/2026 lúc 16:59  
**Sprint Goal:** hoàn thành luồng commerce end-to-end cho nhiều shop.

### Yêu cầu

- CUS-14 đến CUS-17;
- SEL-10, SEL-11;
- ADM-17;
- BON-01;
- NFR-07, NFR-14, NFR-15.

### Ngày 04/08 — Checkout Core

- OrderGroup/Order/OrderItem;
- address và product snapshot;
- order total allocation;
- reserve/trừ kho;
- voucher usage;
- transaction boundary;
- checkout idempotency;
- COD.

### Ngày 05/08 — Payment

- Payment Provider interface;
- payment attempt;
- VNPay/MoMo/Stripe sandbox theo ADR;
- redirect/return;
- callback/IPN;
- signature verification;
- raw payload;
- duplicate callback test;
- refund structure.

### Ngày 06/08 — Order Lifecycle

- state machine;
- OrderStatusHistory;
- Seller xác nhận/đóng gói/giao;
- Customer theo dõi/hủy/mua lại;
- hoàn kho và voucher;
- Admin theo dõi;
- shipping tracking;
- UI ba vai trò;
- E2E smoke test.

### Release Checkpoint

**Release 0.3 — Commerce Core**, deadline 06/08/2026.

---

## Sprint 8 — Review, Return, Dispute & Trust

**Thời gian:** 07–08/08/2026  
**Deadline:** 08/08/2026 lúc 16:59  
**Sprint Goal:** hoàn thành vòng đời sau mua hàng và cơ chế xử lý nội dung/tranh chấp.

### Yêu cầu

- CUS-18, CUS-19;
- SEL-13 đến SEL-15;
- ADM-18;
- BON-10.

### Ngày 07/08

- verified purchase review;
- review media;
- edit window;
- rating aggregation;
- seller reply;
- customer list;
- review report.

### Ngày 08/08

- ReturnRequest/ReturnRequestItem;
- evidence media;
- approve/reject;
- partial/full refund;
- dispute;
- Admin resolution;
- report product/shop/review;
- UI và test.

---

## Sprint 9 — Realtime Chat & Notifications

**Thời gian:** 09–10/08/2026  
**Deadline:** 10/08/2026 lúc 16:59  
**Sprint Goal:** Customer và Seller giao tiếp realtime; sự kiện quan trọng được thông báo.

### Yêu cầu

- SEL-16;
- CUS-20, CUS-21;
- BON-08;
- BON-14 phần realtime;
- AI-05;
- NFR-07.

### Ngày 09/08

- Conversation/Message;
- JWT WebSocket authentication;
- Channels consumer;
- Redis channel layer;
- message persistence;
- text/image/product/order link;
- unread cursor.

### Ngày 10/08

- notification DB và WebSocket;
- order/review/seller/Flash Sale event;
- reconnect;
- polling fallback;
- chatbot tư vấn;
- conversation UI;
- permission/reconnect/provider-failure test.

---

## Sprint 10 — Dashboard, Reports & Administration

**Thời gian:** 11–12/08/2026  
**Deadline:** 12/08/2026 lúc 16:59  
**Sprint Goal:** hoàn thành dashboard, báo cáo, cấu hình và công cụ vận hành.

### Yêu cầu

- ADM-01 đến ADM-03;
- ADM-12;
- ADM-22 đến ADM-26;
- SEL-01;
- BON-11, BON-13;
- AI-14;
- NFR-06, NFR-15, NFR-16.

### Ngày 11/08

- Admin dashboard;
- Seller dashboard;
- revenue/order/customer/product aggregates;
- time filter;
- top product;
- trend product;
- cache và background aggregation.

### Ngày 12/08

- reports;
- import/export Excel;
- audit log UI;
- SiteSetting/feature flag;
- AI sales analytics;
- backup command và restore verification;
- chart UI;
- permission/performance test;
- Release 0.4 smoke test.

### Release Checkpoint

**Release 0.4 — Commerce Complete**, deadline 12/08/2026.

---

## Sprint 11 — AI Platform & Complete AI Features

**Thời gian:** 13–15/08/2026  
**Deadline:** 15/08/2026 lúc 16:59  
**Sprint Goal:** hoàn thành và chuẩn hóa toàn bộ AI-01 đến AI-15.

### Yêu cầu

- AI-01 đến AI-15;
- hoàn thiện lại các AI Story đã phát triển ở Sprint 5, 9 và 10.

### Ngày 13/08

- chuẩn hóa provider interface;
- retry/backoff/timeout;
- AIRequestLog;
- token, cost và latency;
- cache;
- Celery;
- feature flag;
- rate limit và fallback.

### Ngày 14/08

- review summary;
- product/description summary;
- compare products;
- generate product description;
- auto-tag/category;
- translation.

### Ngày 15/08

- price suggestion;
- recommendation tuning;
- chatbot grounding;
- sales analytics narrative;
- UI tất cả tính năng AI;
- nhãn “Tạo bởi AI”;
- security/privacy review;
- provider timeout/cache/cost test;
- regression AI-01 đến AI-15.

---

## Sprint 12 — Bonus Completion, Hardening & Final Release

**Thời gian:** 16–20/08/2026  
**Deadline cuối dự án:** 20/08/2026 lúc 16:59  
**Sprint Goal:** hoàn thành Bonus còn lại, toàn bộ NFR, regression và sản phẩm bàn giao.

### Yêu cầu

- BON-01 đến BON-14, xác nhận hoàn tất toàn bộ;
- hoàn thiện BON-05 Affiliate;
- BON-06 Loyalty;
- BON-07 Wallet;
- BON-11 Import/Export;
- BON-12 QR;
- toàn bộ NFR-01 đến NFR-16;
- toàn bộ tài liệu bàn giao.

### Ngày 16/08 — Bonus Domain

- affiliate link/click/conversion;
- commission record;
- loyalty points ledger;
- wallet transaction ledger;
- QR product/order/shop;
- hoàn tất các Bonus carry-over;
- test balance không âm và idempotency.

### Ngày 17/08 — Functional Regression

- kiểm tra ADM-01 đến ADM-26;
- kiểm tra SEL-01 đến SEL-18;
- kiểm tra CUS-01 đến CUS-22;
- kiểm tra AI-01 đến AI-15;
- kiểm tra BON-01 đến BON-14;
- sửa bug Critical/High.

### Ngày 18/08 — NFR Hardening

- authentication/authorization matrix;
- XSS, upload, rate limit và secrets;
- N+1 và pagination;
- Redis cache;
- Celery retry;
- concurrent inventory/checkout/voucher;
- payment idempotency;
- logging;
- backup/restore;
- test coverage.

### Ngày 19/08 — Deployment & Documentation

- production Docker images;
- `docker-compose.yml`;
- Nginx;
- healthcheck;
- GitHub Actions;
- `.env.example`;
- seed data;
- Swagger/OpenAPI;
- ERD;
- README;
- setup/deployment/backup guide;
- demo script.

### Ngày 20/08 — Final Acceptance

- clean clone test;
- chạy hệ thống từ đầu;
- apply migration;
- seed data;
- chạy toàn bộ test;
- build frontend;
- smoke test toàn bộ vai trò;
- chạy kịch bản demo end-to-end;
- kiểm tra tài liệu;
- đóng bug Critical/High;
- tạo tag `v1.0.0`;
- lưu release note và retrospective cuối dự án.

### Exit Criteria Release 1.0

- toàn bộ 111 yêu cầu có trạng thái Done;
- không có bug Critical/High;
- core coverage đạt tối thiểu 60%;
- concurrent oversell test pass;
- duplicate payment callback test pass;
- Docker/Nginx chạy được;
- CI xanh;
- OpenAPI và ERD khớp code;
- seed data demo hoạt động;
- backup và restore đã thử;
- demo end-to-end thành công.

---

# 9. Ma trận bao phủ yêu cầu theo Sprint

| Nhóm yêu cầu | Sprint chính | Sprint kiểm tra cuối |
|---|---|---|
| ADM-01 đến ADM-03 | S10 | S12 |
| ADM-04 đến ADM-12 | S2, S10 | S12 |
| ADM-13 đến ADM-16 | S3 | S12 |
| ADM-17 đến ADM-21 | S6, S7, S8 | S12 |
| ADM-22 đến ADM-26 | S10 | S12 |
| SEL-01 | S10 | S12 |
| SEL-02 đến SEL-05 | S3 | S12 |
| SEL-06 đến SEL-09 | S4 | S12 |
| SEL-10 đến SEL-12 | S6, S7 | S12 |
| SEL-13 đến SEL-16 | S8, S9 | S12 |
| SEL-17, SEL-18 | S2 | S12 |
| CUS-01 đến CUS-06 | S1 | S12 |
| CUS-07 đến CUS-12 | S5 | S12 |
| CUS-13 đến CUS-17 | S6, S7 | S12 |
| CUS-18 đến CUS-21 | S8, S9 | S12 |
| CUS-22 | S5 và xuyên suốt | S12 |
| AI-01 đến AI-04 | S5 | S11, S12 |
| AI-05 | S9 | S11, S12 |
| AI-06 đến AI-13 | S11 | S12 |
| AI-14 | S10 | S11, S12 |
| AI-15 | S5, S11 | S12 |
| BON-01 | S7 | S12 |
| BON-02 | S5 | S12 |
| BON-03, BON-04 | S6 | S12 |
| BON-05 đến BON-07 | S12 | S12 |
| BON-08 | S9 | S12 |
| BON-09 | S4 | S12 |
| BON-10 | S8 | S12 |
| BON-11 | S10 | S12 |
| BON-12 | S12 | S12 |
| BON-13 | S10 | S12 |
| BON-14 | S6, S9 | S12 |
| NFR-01 đến NFR-04 | S0–S2 | S12 |
| NFR-05, NFR-06 | S3–S10 | S12 |
| NFR-07 | S7–S9 | S12 |
| NFR-08 đến NFR-13 | S0 và xuyên suốt | S12 |
| NFR-14 | S4, S6, S7 | S12 |
| NFR-15 | S0, S2, S7, S10 | S12 |
| NFR-16 | S0, S10 | S12 |

---

# 10. Release Plan

| Release | Deadline | Nội dung |
|---|---|---|
| `v0.1.0` | 26/07/2026 | Auth, RBAC, Admin user, Seller onboarding |
| `v0.2.0` | 30/07/2026 | Shop, catalog, variant, inventory |
| `v0.3.0` | 06/08/2026 | Storefront, cart, voucher, checkout, payment, order |
| `v0.4.0` | 12/08/2026 | Review, return, realtime, dashboard, reports |
| `v0.9.0` | 15/08/2026 | Toàn bộ AI hoàn thành |
| `v1.0.0` | 20/08/2026 | Toàn bộ 111 yêu cầu, NFR, bonus và tài liệu |

Mỗi Release phải:

- tạo Git tag;
- có release note;
- chạy smoke test;
- lưu known issues;
- cập nhật Product Backlog;
- xác nhận migration và seed data.

---

# 11. Definition of Ready

Một User Story chỉ được đưa vào Sprint khi:

- [ ] Có mã yêu cầu;
- [ ] Có mô tả và giá trị nghiệp vụ;
- [ ] Có Acceptance Criteria kiểm thử được;
- [ ] Đã xác định role và permission;
- [ ] Đã xác định API/UI;
- [ ] Đã xác định database change;
- [ ] Dependency đã biết;
- [ ] Có happy path và failure path;
- [ ] Có thiết kế concurrency/idempotency nếu liên quan;
- [ ] Có test case;
- [ ] Có estimate;
- [ ] Đủ nhỏ để tạo vertical slice trong Sprint;
- [ ] Không còn quyết định kiến trúc quan trọng chưa chốt.

Với checkout, payment, inventory, voucher, wallet, loyalty và AI, phải có thêm:

- transaction boundary;
- retry/idempotency;
- rollback/fallback;
- security;
- concurrency;
- audit/logging;
- cleanup hoặc expiry job.

---

# 12. Definition of Done

Một User Story chỉ được xem là Done khi:

- [ ] Acceptance Criteria đạt;
- [ ] Database migration cập nhật;
- [ ] API/OpenAPI cập nhật;
- [ ] Backend và Frontend tích hợp;
- [ ] Business logic nằm đúng Service Layer/composable/store;
- [ ] Permission và tenant isolation pass;
- [ ] Unit test có cho logic quan trọng;
- [ ] API/integration test pass;
- [ ] UI có loading, empty và error state;
- [ ] Error path đã xử lý;
- [ ] Logging cần thiết đã có;
- [ ] Không có secret/debug code;
- [ ] Lint, type check, test và build pass;
- [ ] Đã tự review bằng PR checklist;
- [ ] Tài liệu cập nhật;
- [ ] Đã demo bằng dữ liệu thật/seed;
- [ ] Không có bug Critical/High;
- [ ] Product Owner self-check đã chấp nhận.

Tiêu chí cấp dự án:

- cart, checkout, voucher và inventory coverage tối thiểu 60%;
- có test concurrent chống oversell;
- callback payment idempotent;
- Seller A không truy cập dữ liệu Seller B;
- AI timeout không làm hỏng commerce core;
- Docker/Nginx chạy được bằng tài liệu;
- backup/restore đã kiểm chứng;
- không merge khi CI fail.

---

# 13. Chiến lược kiểm thử

## 13.1. Test Pyramid

```text
E2E cho luồng quan trọng
Integration/API/WebSocket test
Unit test service/store/component
```

## 13.2. Test theo domain

| Domain | Test tối thiểu |
|---|---|
| Authentication | register, verify, login, Google, refresh, logout, locked user |
| Authorization | sai role, sai owner, Seller A/Seller B |
| Catalog | draft/approved/hidden/deleted, filter, upload |
| Inventory | stock in/out, reservation, không âm, concurrent |
| Promotion | expiry, quota, scope, stacking, Flash Sale concurrency |
| Checkout | multi-shop, snapshot, rollback, idempotency |
| Payment | signature, duplicate callback, failed callback, refund |
| Order | transition, cancel rollback, reorder, tracking |
| Review/Return | verified purchase, unique, edit, partial return, dispute |
| WebSocket | auth, conversation permission, reconnect, fallback |
| Dashboard | aggregate đúng, filter thời gian, tenant scope |
| AI | timeout, retry, fallback, cache, cost log, content label |
| Wallet/Point | ledger, balance, duplicate event, không âm |
| DevOps | migration, healthcheck, clean clone, backup/restore |

## 13.3. Regression bắt buộc cuối mỗi Sprint

- toàn bộ Backend test;
- Frontend unit test;
- frontend build;
- migration check;
- OpenAPI generation check;
- smoke test Sprint Goal;
- permission smoke test;
- ghi bug vào backlog.

---

# 14. Git và tự review

## 14.1. Branch

```text
main
└── develop
    ├── feature/CUS-14-checkout
    ├── feature/SEL-06-stock-entry
    ├── fix/BUG-027-payment-callback
    └── docs/ADR-003-inventory-reservation
```

## 14.2. Commit

```text
feat: add multi-shop checkout (CUS-14)
fix: prevent duplicate payment callback (CUS-15)
test: add concurrent inventory test (NFR-14)
docs: update order database design
```

## 14.3. Self Pull Request

Dù là dự án cá nhân, mỗi Story quan trọng vẫn tạo PR vào `develop` để tạo điểm tự review.

Checklist:

- [ ] Liên kết Story;
- [ ] giải thích thay đổi;
- [ ] screenshot/video UI;
- [ ] migration đã kiểm tra;
- [ ] API contract cập nhật;
- [ ] permission kiểm tra;
- [ ] test mới và test cũ pass;
- [ ] không chứa secret;
- [ ] tài liệu cập nhật;
- [ ] hướng dẫn test thủ công;
- [ ] đọc lại diff sau ít nhất một lần chuyển ngữ cảnh.

Không tự merge khi CI fail.

---

# 15. Quy trình làm việc hằng ngày

## Buổi đầu ngày

1. Daily Scrum cá nhân.
2. Xem burndown và deadline Sprint.
3. Chọn một Story theo WIP limit.
4. Xác nhận Acceptance Criteria.
5. Tạo branch và task checklist.

## Trong ngày

1. Thiết kế thay đổi nhỏ cần thiết.
2. Viết test quan trọng trước hoặc cùng code.
3. Hoàn thành Backend/API.
4. Hoàn thành Frontend.
5. Tích hợp và xử lý error state.
6. Chạy test cục bộ thường xuyên.
7. Commit nhỏ theo logic.

## Cuối ngày

1. Chạy lint, type check, test và build.
2. Tự review diff.
3. Cập nhật OpenAPI/ERD/tài liệu.
4. Ghi daily log.
5. Cập nhật trạng thái backlog.
6. Refinement Story của ngày kế tiếp.
7. Ghi blocker và carry-over.

Mẫu daily log:

```text
Ngày:
Sprint:
Đã hoàn thành:
Đang dở:
Test đã chạy:
Bug phát hiện:
Blocker:
Quyết định kỹ thuật:
Kế hoạch ngày mai:
```

---

# 16. Risk Register

| Rủi ro | Xác suất | Ảnh hưởng | Giảm thiểu |
|---|---|---|---|
| Một cá nhân triển khai 111 yêu cầu trong 30 ngày | Rất cao | Rất cao | WIP=1, vertical slice, tự động hóa, checkpoint mỗi ngày, không Done giả |
| Không có ngày dự phòng | Rất cao | Cao | hấp thụ carry-over ngay Sprint kế tiếp; dành 5 ngày cho Sprint 12 |
| Checkout nhiều shop phức tạp | Cao | Rất cao | ADR, sequence, Sprint 7 ba ngày, idempotency |
| Oversell tồn kho | Cao | Rất cao | row lock/F expression, ledger, concurrent test |
| Callback thanh toán trùng | Cao | Rất cao | unique event, raw payload, idempotency |
| Seller truy cập shop khác | Trung bình | Rất cao | tenant scope từ request.user, permission test |
| Frontend/Backend lệch contract | Cao | Cao | OpenAPI-first, shared types, kiểm tra mỗi ngày |
| AI provider lỗi/tốn chi phí | Trung bình | Cao | cache, timeout, budget log, feature flag, fallback |
| WebSocket mất kết nối | Trung bình | Trung bình | DB persistence, reconnect, polling |
| Wallet/loyalty sai số dư | Cao | Rất cao | append-only ledger, transaction, idempotency |
| Test bị dồn cuối tháng | Cao | Rất cao | test trong DoD và regression cuối mỗi Sprint |
| Tài liệu lệch code | Cao | Cao | cập nhật trong cùng Story, docs check ở PR |
| Thiếu dữ liệu demo | Trung bình | Cao | seed data từ Sprint 0, cập nhật mỗi Release |
| Kiệt sức do lịch liên tục | Cao | Cao | time-box, nghỉ ngắn, giới hạn WIP, tránh context switching |

---

# 17. Spike và Architecture Decision Record

Các Spike phải hoàn thành trong Sprint 0; chỉ refinement nhỏ được phép tiếp tục sau đó.

| Spike | Quyết định |
|---|---|
| SPIKE-001 | OrderGroup/Order/Payment và transaction boundary |
| SPIKE-002 | Inventory reservation, expiry, release |
| SPIKE-003 | Payment sandbox và callback |
| SPIKE-004 | AI provider, embedding model, dimension |
| SPIKE-005 | Media storage và cleanup |
| SPIKE-006 | PK/public ID strategy |

Lưu tại:

```text
docs/adr/
├── ADR-001-primary-key-strategy.md
├── ADR-002-order-group-model.md
├── ADR-003-inventory-reservation.md
├── ADR-004-payment-provider.md
├── ADR-005-ai-provider.md
└── ADR-006-media-storage.md
```

---

# 18. Tài liệu phải duy trì trong quá trình phát triển

```text
docs/
├── agile/
│   ├── AGILE_PROJECT_PLAN.md
│   ├── PRODUCT_BACKLOG.md
│   ├── RELEASE_PLAN.md
│   ├── DEFINITION_OF_READY.md
│   ├── DEFINITION_OF_DONE.md
│   ├── RISK_REGISTER.md
│   ├── daily-logs/
│   └── retrospectives/
├── adr/
├── basic-design/
├── database/
│   └── DATABASE_DESIGN.md
├── api/
├── workflows/
├── test/
└── deployment/
```

Tài liệu bàn giao tối thiểu:

- README;
- Project Overview;
- Basic Design;
- Database Design và ERD;
- API/OpenAPI;
- business rules;
- workflow/state machine;
- permission matrix;
- deployment guide;
- backup/restore guide;
- test report;
- AI design;
- release note;
- demo script.

---

# 19. Bảng theo dõi Sprint

Mỗi Sprint dùng bảng:

| Story | Trạng thái | Backend | Frontend | Test | Docs | Blocker |
|---|---|---:|---:|---:|---:|---|
| Mã Story | Todo/In Progress/Test/Done | % | % | % | % | Nội dung |

Quy tắc:

- không dùng tỷ lệ 100% nếu Acceptance Criteria chưa pass;
- `Done` chỉ dùng khi toàn bộ cột hoàn thành;
- carry-over phải ghi lý do;
- blocker quá 4 giờ phải được xử lý ưu tiên;
- cuối Sprint lưu retrospective.

---

# 20. Tiêu chí chấp nhận cuối dự án

Dự án được xem là hoàn thành vào **20/08/2026** khi:

- [ ] ADM-01 đến ADM-26 hoàn thành;
- [ ] SEL-01 đến SEL-18 hoàn thành;
- [ ] CUS-01 đến CUS-22 hoàn thành;
- [ ] AI-01 đến AI-15 hoàn thành;
- [ ] BON-01 đến BON-14 hoàn thành;
- [ ] NFR-01 đến NFR-16 hoàn thành;
- [ ] toàn bộ migration chạy trên database sạch;
- [ ] seed data tạo được môi trường demo;
- [ ] API docs khớp implementation;
- [ ] ERD khớp model;
- [ ] permission matrix pass;
- [ ] concurrent test pass;
- [ ] payment idempotency pass;
- [ ] core coverage tối thiểu 60%;
- [ ] Frontend lint/test/build pass;
- [ ] Backend lint/test pass;
- [ ] Docker/Nginx healthcheck pass;
- [ ] backup/restore pass;
- [ ] không có bug Critical/High;
- [ ] demo end-to-end thành công;
- [ ] tag `v1.0.0` được tạo.

---

# 21. Kết luận

Kế hoạch này giữ nguyên toàn bộ chức năng, use case, Bonus và yêu cầu phi chức năng của đặc tả. Phạm vi không bị cắt giảm vì giới hạn một tháng.

Ba nguyên tắc quan trọng nhất:

1. **Mỗi Story phải hoàn thành theo vertical slice**, không để Backend, Frontend, test hoặc tài liệu tách rời.
2. **Các domain tài chính và dữ liệu nhạy cảm phải giữ đầy đủ transaction, idempotency, audit và concurrency test**, dù deadline ngắn.
3. **Không đánh dấu Done để chạy theo lịch**; deadline chỉ có ý nghĩa khi Increment có thể chạy, kiểm thử và demo.

Các mốc chính:

```text
26/07/2026: Release 0.1 — Auth, RBAC, Seller Onboarding
30/07/2026: Release 0.2 — Catalog & Inventory
06/08/2026: Release 0.3 — Commerce Core
12/08/2026: Release 0.4 — Commerce Complete
15/08/2026: Release 0.9 — AI Complete
20/08/2026: Release 1.0 — Full Scope Final Submission
```
