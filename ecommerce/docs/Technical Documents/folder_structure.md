# Folder Structure

Cấu trúc thư mục đầy đủ của repository, cụ thể hóa `ARCHITECTURE.md` (mục 2–3) và `TECH_STACK.md`. Đây là cấu trúc **tham chiếu** khi khởi tạo dự án — giữ nhất quán để bất kỳ ai (hoặc AI) cũng biết code mới nên đặt ở đâu.

---

## 1. Cấu trúc gốc (Repository Root)

```
multi-vendor-ai-ecommerce/
├── backend/                      # Django project
├── frontend/                      # Vue 3 project
├── docs/                           # Toàn bộ tài liệu dự án (các file .md đã tạo)
│   ├── PROJECT_CONSTITUTION.md
│   ├── PROJECT_OVERVIEW.md
│   ├── TECH_STACK.md
│   ├── ARCHITECTURE.md
│   ├── CODING_STANDARDS.md
│   ├── roles.md
│   ├── modules.md
│   ├── use_cases.md
│   ├── business_rules.md
│   ├── workflows.md
│   ├── database_design.md
│   ├── api_design.md
│   ├── coding_patterns.md
│   ├── security.md
│   ├── testing_strategy.md
│   ├── folder_structure.md
│   └── erd.png                       # Sơ đồ ERD xuất từ dbdiagram.io (NFR-10)
├── nginx/
│   ├── nginx.conf
│   └── Dockerfile
├── .github/
│   └── workflows/
│       └── ci.yml                     # Pipeline lint + test + build (mục CI/CD)
├── docker-compose.yml
├── docker-compose.dev.yml               # Override cho môi trường dev (hot-reload, debug)
├── .env.example
├── .gitignore
└── README.md
```

---

## 2. Backend (`backend/`)

```
backend/
├── config/                          # Django project settings (tên "config" thay vì tên project mặc định)
│   ├── settings/
│   │   ├── base.py                    # Cấu hình chung
│   │   ├── development.py
│   │   ├── production.py
│   │   └── test.py
│   ├── urls.py                        # Root URL conf, include từng app
│   ├── asgi.py                          # Cho Django Channels (WebSocket)
│   ├── wsgi.py
│   └── celery.py                         # Khởi tạo Celery app
│
├── apps/
│   ├── account/                     # Module 1: Account & Auth
│   │   ├── models.py                    # User, CustomerProfile, SellerProfile, AdminProfile, Address
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services.py
│   │   ├── permissions.py
│   │   ├── validators.py
│   │   ├── selectors.py
│   │   ├── tasks.py                       # Gửi email xác thực, reset mật khẩu
│   │   ├── signals.py
│   │   └── tests/
│   │
│   ├── seller_onboarding/             # Module 2
│   │   ├── models.py                      # (dùng chung SellerProfile ở account, chỉ chứa logic duyệt)
│   │   ├── services.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── tests/
│   │
│   ├── catalog/                        # Module 3: Category, Brand
│   │   ├── apps.py
│   │   ├── admin.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services.py
│   │   ├── selectors.py
│   │   ├── migrations/
│   │   ├── README.md
│   │   └── tests/
│   │
│   ├── shop/                             # Module 6: Shop, ShopFollower
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services.py
│   │   ├── permissions.py                    # IsShopOwner
│   │   └── tests/
│   │
│   ├── product/                          # Module 4: Product, Variant, Media, Attribute
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services.py
│   │   ├── state_machine.py                 # ProductStateMachine
│   │   ├── repositories.py
│   │   ├── selectors.py
│   │   ├── permissions.py
│   │   ├── validators.py
│   │   ├── signals.py                        # Cập nhật avg_rating, trigger re-index embedding
│   │   ├── migrations/
│   │   ├── README.md
│   │   └── tests/
│   │
│   ├── inventory/                          # Module 5: StockEntry, StockMovement, StockAlert
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services.py
│   │   ├── repositories.py                     # StockRepository — điểm ghi tồn kho duy nhất
│   │   ├── tasks.py                              # Quét sản phẩm sắp hết hàng định kỳ
│   │   └── tests/
│   │       └── test_concurrency.py                 # Test bắt buộc chống oversell
│   │
│   ├── cart/                                  # Module 7
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services.py
│   │   └── tests/
│   │
│   ├── order/                                    # Module 8: Order, OrderItem, OrderStatusHistory
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services.py
│   │   ├── state_machine.py                          # OrderStateMachine
│   │   ├── exceptions.py
│   │   ├── permissions.py
│   │   ├── selectors.py
│   │   ├── tasks.py
│   │   └── tests/
│   │       ├── test_order_service.py
│   │       ├── test_order_state_machine.py
│   │       └── test_checkout_api.py
│   │
│   ├── payment/                                    # Module 9: PaymentTransaction + gateway providers
│   │   ├── models.py
│   │   ├── views.py                                  # Bao gồm endpoint callback
│   │   ├── urls.py
│   │   ├── services.py
│   │   ├── providers/
│   │   │   ├── base.py
│   │   │   ├── vnpay_provider.py
│   │   │   └── cod_provider.py
│   │   └── tests/
│   │
│   ├── return_dispute/                              # Module Return & Dispute (thuộc mục 8 modules.md)
│   │   ├── models.py                                  # ReturnRequest, Dispute
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services.py
│   │   ├── state_machine.py
│   │   └── tests/
│   │
│   ├── promotion/                                       # Module 10: Coupon, FlashSale, Banner, Bundle
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services.py
│   │   ├── tasks.py                                       # Celery beat: kích hoạt/kết thúc Flash Sale
│   │   └── tests/
│   │
│   ├── review/                                             # Module 11: Review, Question, Answer, Report
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services.py
│   │   ├── signals.py                                        # Cập nhật avg_rating của Product
│   │   └── tests/
│   │
│   ├── wishlist/                                              # Module 12
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── tests/
│   │
│   ├── search/                                                  # Module 13: tích hợp Product + AI Service
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services.py
│   │   └── tests/
│   │
│   ├── chat/                                                      # Module 14: Conversation, Message + Consumer
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── consumers.py                                            # Django Channels WebSocket consumer
│   │   ├── routing.py                                                # WebSocket URL routing
│   │   ├── services.py
│   │   └── tests/
│   │
│   ├── notification/                                                  # Module 15
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── consumers.py
│   │   ├── routing.py
│   │   ├── services.py                                                    # NotificationService dùng chung
│   │   └── tests/
│   │
│   ├── report/                                                          # Module 16: dashboard, thống kê, export
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services.py
│   │   ├── tasks.py                                                        # Export Excel/PDF chạy nền
│   │   └── tests/
│   │
│   ├── audit/                                                              # Module 17
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── middleware.py                                                     # hoặc dùng signals thay thế
│   │   └── tests/
│   │
│   ├── system_config/                                                          # Module 18: SiteSetting
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services.py                                                          # đọc config có cache
│   │   └── tests/
│   │
│   ├── ai_service/                                                                # Module 19 — hạ tầng AI dùng chung
│   │   ├── models.py                                                                # AIRequestLog, ProductEmbedding, ProductAISummary, ProductTranslation
│   │   ├── service.py                                                                # AIService — điểm gọi duy nhất
│   │   ├── providers/
│   │   │   ├── base.py
│   │   │   ├── openai_provider.py
│   │   │   ├── claude_provider.py
│   │   │   └── gemini_provider.py
│   │   ├── prompts/                                                                    # Template prompt tách riêng khỏi code logic
│   │   │   ├── product_description.py
│   │   │   ├── review_summary.py
│   │   │   ├── shopping_assistant.py
│   │   │   └── sales_analytics.py
│   │   ├── views.py                                                                      # Endpoint /ai/*
│   │   ├── urls.py
│   │   ├── tasks.py                                                                        # Re-index embeddings, tóm tắt review theo lịch
│   │   └── tests/
│   │
│   ├── bonus/                                                                              # Các tính năng Bonus nhỏ, gom chung hoặc tách app riêng nếu lớn
│   │   ├── shipping_tracking/
│   │   ├── affiliate/
│   │   ├── loyalty/                                                                             # PointTransaction, WalletTransaction
│   │   ├── waitlist/
│   │   └── reports_abuse/
│   │
│   └── common/                                                                                # Dùng chung toàn dự án
│       ├── responses.py                                                                          # success_response/error_response
│       ├── exception_handler.py
│       ├── exceptions.py                                                                            # BusinessError và các exception dùng chung
│       ├── pagination.py
│       ├── permissions.py                                                                            # Permission base dùng chung nhiều app
│       └── middleware.py                                                                              # request_id, v.v.
│
├── tests/
│   ├── factories.py                                                                                   # factory_boy dùng chung
│   └── conftest.py                                                                                       # fixture pytest dùng chung (api_client, authenticated_client...)
│
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
│
├── Dockerfile                                                                                              # Multi-stage build
├── manage.py
└── pytest.ini
```

---

## 3. Frontend (`frontend/`)

```
frontend/
├── src/
│   ├── features/                        # Domain-driven — mỗi domain là 1 feature (khớp ARCHITECTURE.md mục 3)
│   │   ├── auth/
│   │   │   ├── components/
│   │   │   ├── composables/
│   │   │   ├── store.ts
│   │   │   ├── api.ts
│   │   │   ├── types.ts
│   │   │   └── pages/                       # Trang cấp route (Login.vue, Register.vue...)
│   │   │
│   │   ├── product/
│   │   │   ├── components/                    # ProductCard, ProductGallery, VariantSelector...
│   │   │   ├── composables/
│   │   │   ├── store.ts
│   │   │   ├── api.ts
│   │   │   ├── types.ts
│   │   │   └── pages/                            # ProductListPage.vue, ProductDetailPage.vue
│   │   │
│   │   ├── cart/
│   │   ├── checkout/
│   │   ├── order/
│   │   ├── wishlist/
│   │   ├── review/
│   │   ├── chat/
│   │   │   └── composables/
│   │   │       └── useConversationSocket.ts
│   │   ├── notification/
│   │   │   └── composables/
│   │   │       └── useNotificationSocket.ts
│   │   ├── search/
│   │   ├── ai-assistant/                             # Chat widget AI Shopping Assistant
│   │   │
│   │   ├── seller-dashboard/                            # Toàn bộ khu vực quản trị Seller
│   │   │   ├── product-management/
│   │   │   ├── inventory-management/
│   │   │   ├── order-management/
│   │   │   ├── promotion-management/
│   │   │   └── pages/
│   │   │
│   │   └── admin-dashboard/                                # Toàn bộ khu vực quản trị Admin
│   │       ├── user-management/
│   │       ├── seller-management/
│   │       ├── product-moderation/
│   │       ├── promotion-management/
│   │       ├── report/
│   │       ├── audit-log/
│   │       ├── system-config/
│   │       └── pages/
│   │
│   ├── shared/                                                # Dùng chung nhiều feature
│   │   ├── components/                                          # Button, Modal, Pagination, Skeleton...
│   │   ├── composables/                                            # useDebounce, usePagination...
│   │   ├── lib/
│   │   │   ├── http.ts                                               # axios instance + interceptor
│   │   │   └── formatters.ts                                          # format tiền VNĐ, ngày giờ VN
│   │   └── types/
│   │       └── api.ts                                                  # ApiResponse<T>, PaginationMeta
│   │
│   ├── stores/
│   │   └── auth.ts                                                       # Store toàn cục (không thuộc riêng feature nào)
│   │
│   ├── router/
│   │   ├── index.ts
│   │   ├── guards.ts                                                       # Route guard theo role
│   │   └── routes/
│   │       ├── public.routes.ts
│   │       ├── customer.routes.ts
│   │       ├── seller.routes.ts
│   │       └── admin.routes.ts
│   │
│   ├── layouts/
│   │   ├── CustomerLayout.vue
│   │   ├── SellerLayout.vue
│   │   └── AdminLayout.vue
│   │
│   ├── assets/
│   ├── App.vue
│   └── main.ts
│
├── tests/
│   └── setup.ts                                                              # Cấu hình vitest chung
│
├── public/
├── index.html
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.js
├── .eslintrc.cjs
├── Dockerfile                                                                   # Multi-stage: build Vite → Nginx serve
└── package.json
```

---

## 4. Nguyên tắc đặt tên & vị trí file (tóm tắt)

| Loại nội dung | Đặt ở đâu |
|---|---|
| Model, logic nghiệp vụ của 1 domain | `apps/<domain>/` (Backend) |
| Logic dùng chung nhiều domain (response format, exception) | `apps/common/` |
| Component/logic chỉ dùng trong 1 domain | `features/<domain>/` (Frontend) |
| Component/composable dùng ≥ 2 domain | `shared/` (Frontend) |
| Trang có route riêng | `features/<domain>/pages/` |
| WebSocket consumer | `apps/<domain>/consumers.py` + `routing.py` |
| Celery task định kỳ | `apps/<domain>/tasks.py` + đăng ký ở `config/celery.py` |
| Prompt template AI | `apps/ai_service/prompts/` — tách khỏi `service.py` để dễ chỉnh sửa không đụng logic |
| Test | luôn nằm cạnh code trong `tests/` của từng app/feature, không gom hết vào 1 thư mục test tổng (trừ `factories.py`/`conftest.py` dùng chung) |

## 5. Tài liệu liên quan

- `ARCHITECTURE.md` mục 2–3 — lý do đằng sau cấu trúc Backend/Frontend ở trên.
- `modules.md` — mapping đầy đủ giữa module nghiệp vụ và Django app tương ứng.
- `coding_patterns.md` — nội dung cụ thể bên trong từng file (`services.py`, `selectors.py`...).
- `TECH_STACK.md` — công nghệ tương ứng với từng thư mục cấu hình (Vite, Tailwind, Celery...).
