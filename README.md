# CE Training

Repository thực hành và phát triển kỹ năng Full-stack thông qua một sản phẩm thực tế: **Multi-Vendor AI E-commerce Platform**. Dự án hướng đến một sàn thương mại điện tử đa gian hàng, hỗ trợ ba vai trò **Admin**, **Seller** và **Customer**, đồng thời xây dựng lớp dịch vụ AI có thể thay đổi nhà cung cấp.

> Trạng thái: đang phát triển. Nền tảng hệ thống, xác thực, phân quyền và nhóm chức năng quản lý tài khoản đã được khởi tạo; các module thương mại điện tử và AI sẽ được bổ sung theo lộ trình.

## Mục tiêu dự án

- Thực hành quy trình xây dựng một ứng dụng Full-stack có kiến trúc rõ ràng và dễ mở rộng.
- Xây dựng đầy đủ các nghiệp vụ của sàn thương mại điện tử đa gian hàng.
- Áp dụng xác thực JWT, phân quyền theo vai trò, xử lý bất đồng bộ và giao tiếp thời gian thực.
- Tích hợp tìm kiếm ngữ nghĩa, gợi ý sản phẩm và trợ lý mua sắm qua một AI Service Layer thống nhất.
- Chuẩn hóa môi trường phát triển, kiểm thử và triển khai bằng Docker.

## Chức năng chính

| Nhóm | Phạm vi |
| --- | --- |
| Admin | Quản lý người dùng, seller, sản phẩm, đơn hàng, khuyến mãi, báo cáo và audit log |
| Seller | Quản lý gian hàng, sản phẩm, biến thể, tồn kho, đơn hàng, voucher và hội thoại với khách hàng |
| Customer | Tài khoản, tìm kiếm, wishlist, giỏ hàng, checkout, thanh toán, theo dõi đơn và đánh giá |
| AI | Smart search, semantic search, gợi ý cá nhân hóa, chatbot, sinh nội dung và phân tích bán hàng |
| Nền tảng | JWT, RBAC, Celery, Redis cache, WebSocket, OpenAPI, logging và health check |

## Công nghệ

- **Frontend:** Vue 3, TypeScript, Vite, Pinia, Vue Router, Tailwind CSS, Axios, Vitest.
- **Backend:** Python 3.12, Django 5, Django REST Framework, Simple JWT, Channels, Celery.
- **Dữ liệu:** PostgreSQL với `pg_trgm` và `pgvector`; Redis 7 cho cache, task queue và channel layer.
- **AI và thanh toán:** AI Service Layer đa nhà cung cấp (mặc định Gemini), COD và VNPay Sandbox.
- **Hạ tầng:** Docker Compose, Nginx và OpenAPI/Swagger.

## Cấu trúc repository

```text
CE_Training/
├── README.md
└── ecommerce/
    ├── backend/              # Django API, domain apps, Celery và Channels
    ├── frontend/             # Vue SPA tổ chức theo feature
    ├── nginx/                # Reverse proxy và phục vụ static/media
    ├── docs/                 # Đặc tả, kiến trúc và quy chuẩn dự án
    ├── docker-compose.yml    # Cấu hình chạy gần với production
    ├── docker-compose.dev.yml
    └── .env.example
```

## Khởi chạy nhanh

### Yêu cầu

- Docker và Docker Compose v2.
- PostgreSQL có thể truy cập từ Docker.
- Database đã bật extension `pg_trgm` và `vector`.

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS vector;
```

### Cấu hình môi trường

```bash
cd ecommerce
cp .env.example .env
```

Cập nhật tối thiểu các biến `DJANGO_SECRET_KEY`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` và `POSTGRES_HOST`. Không commit file `.env`.

### Chạy môi trường development

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Sau khi các container hoạt động:

- Ứng dụng: <http://localhost:8080>
- Frontend Vite: <http://localhost:5173>
- Backend API: <http://localhost:8000>
- Health check: <http://localhost:8080/api/health/>
- Swagger UI: <http://localhost:8080/api/docs/>

Chạy migration lần đầu:

```bash
docker compose run --rm backend python manage.py migrate
```

## Kiểm tra chất lượng

Backend:

```bash
cd ecommerce/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements/development.txt
ruff check .
python manage.py check
pytest
```

Frontend:

```bash
cd ecommerce/frontend
npm ci
npm run lint
npm run test
npm run build
```

## Tài liệu

- [Tổng quan sản phẩm](ecommerce/docs/PROJECT_OVERVIEW.md)
- [Kiến trúc hệ thống](ecommerce/docs/ARCHITECTURE.md)
- [Technology stack](ecommerce/docs/TECH_STACK.md)
- [Quy chuẩn lập trình](ecommerce/docs/CODING_STANDARDS.md)
- [Project Constitution](ecommerce/docs/PROJECT_CONSTITUTION.md)
- [Hướng dẫn chi tiết dự án e-commerce](ecommerce/README.md)

## Quy trình Git đề xuất

- `main`: phiên bản ổn định.
- `develop`: tích hợp các thay đổi đã hoàn thiện.
- `feature/<ten-tinh-nang>`: phát triển từng chức năng độc lập.

Commit nên ngắn gọn, mô tả đúng phạm vi thay đổi và không chứa secrets, file `.env`, dependency cache hoặc build artifacts.

## License

Dự án được xây dựng cho mục đích học tập và thực hành.
